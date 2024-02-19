import logging
import mimetypes
import os
import time
from typing import List, Optional, Tuple

from langchain import callbacks
from langchain.callbacks.tracers.langchain import wait_for_all_tracers
from langchain_community.chat_models import AzureChatOpenAI, ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import Client

from schema import AlttexterResponse, ImageAltText


def alttexter(input_text: str, images: dict, image_urls: List[str]) -> Tuple[List[ImageAltText], Optional[str]]:

    """
    Processes input text and images to generate alt text and title attributes.

    Args:
        input_text (str): Article text.
        images (dict): Base64 encoded images.
        image_urls (List[str]): Image URLs.

    Returns:
        Tuple[AlttexterResponse, str]: Generated alt texts and optional tracing URL.
    """

    if os.getenv('ALTTEXTER_MODEL') == 'openai':
        llm = ChatOpenAI(
            verbose=True,
            temperature=0,
            model="gpt-4-vision-preview",
            max_tokens=4096
        )
    elif os.getenv('ALTTEXTER_MODEL') == 'openai_azure':
        llm = AzureChatOpenAI(
            verbose=True,
            temperature=0,  
            openai_api_version="2024-02-15-preview",
            azure_deployment=os.getenv("AZURE_DEPLOYMENT", "vision-preview"),
            model="vision-preview",
            max_tokens=4096
        )
    else:
        error_message = f"Unsupported model specified: {os.getenv('ALTTEXTER_MODEL')}"
        raise ValueError(error_message)

    content = [
        {
            "type": "text",
            "text": f"""ARTICLE:

{input_text}
            """
        }
    ]

    # Process images and add to content
    for image_name, base64_string in images.items():
        mime_type, _ = mimetypes.guess_type(image_name)
        if not mime_type:
            logging.warning(f"Could not determine MIME type for image: {image_name}")
            continue

        image_entry = {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{base64_string}",
                "detail": "auto",
            }
        }
        content.append(image_entry)

    # Add image URLs to content
    for url in image_urls:
        image_entry = {
            "type": "image_url",
            "image_url": {
                "url": url,
                "detail": "auto",
            }
        }
        content.append(image_entry)

    parser = PydanticOutputParser(pydantic_object=AlttexterResponse)
    all_image_identifiers = list(images.keys()) + image_urls

    messages = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content='''You are a world-class expert at generating concise alternative text and title attributes for images defined in technical articles written in markdown format.\nFor each image in the article use a contextual understanding of the article text and the image itself to generate a concise alternative text and title attribute.\n{format_instructions}'''.format(format_instructions=parser.get_format_instructions())),
            HumanMessage(content=content),
            HumanMessage(
                content=f"Tip: List of file names of images including their paths or URLs: {str(all_image_identifiers)}"
            ),
        ]
    )

    alttexts = None
    run_url = None

    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
    if tracing_enabled:
        client = Client()
        try:
            with callbacks.collect_runs() as cb:
                alttexts = llm.invoke(messages.format_messages())

                # Ensure that all tracers complete their execution
                wait_for_all_tracers()

                if alttexts:
                    # Get public URL for run
                    run_id = cb.traced_runs[0].id
                    time.sleep(2)
                    client.share_run(run_id)
                    run_url = client.read_run_shared_link(run_id)
        except Exception as e:
            logging.error(f"Error during LLM invocation with tracing: {str(e)}")
    else:
        try:
            alttexts = llm.invoke(messages.format_messages())
        except Exception as e:
            logging.error(f"Error during LLM invocation without tracing: {str(e)}")

    if alttexts:
        try:
            alttexts_parsed = parser.parse(alttexts.content)
            return alttexts_parsed, run_url
        except Exception as e:
            logging.error(f"Error parsing LLM response: {str(e)}")

    return None, run_url
