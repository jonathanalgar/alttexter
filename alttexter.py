import base64
import logging
import mimetypes
import os
import time
from typing import List, Optional, Tuple

import cairosvg
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langfuse.callback import CallbackHandler

from schema import AlttexterResponse, ImageAltText

langfuse_handler = CallbackHandler(
    public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
    secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
    host=os.getenv('LANGFUSE_HOST')
)


def determine_llm() -> ChatOpenAI:
    """Determine which LLM to use based on environment variable."""
    model_env = os.getenv("ALTTEXTER_MODEL")
    if model_env == "openai":
        return ChatOpenAI(verbose=True,
                          temperature=0,
                          model="gpt-4-vision-preview",
                          max_tokens=4096)
    elif model_env == "openai_azure":
        return AzureChatOpenAI(verbose=True,
                               temperature=0, openai_api_version="2024-02-15-preview",
                               azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                               model="vision-preview",
                               max_tokens=4096)
    else:
        raise ValueError(f"Unsupported model specified: {model_env}")

def svg_to_png_base64(svg_data):
    """
    Converts SVG data to PNG and returns the base64 encoded PNG image.

    Args:
        svg_data (str): The SVG data as a string.

    Returns:
        str: The base64 encoded PNG image.
    """
    png_data = cairosvg.svg2png(bytestring=svg_data)

    return base64.b64encode(png_data).decode('utf-8')

def alttexter(input_text: str, images: dict, image_urls: List[str]) -> Tuple[List[ImageAltText], Optional[str]]:
    """
    Processes input text and images to generate alt text and title attributes.

    Args:
        input_text (str): The article text to provide context for image alt text generation.
        images (dict): A dictionary of images where keys are image names and values are base64 encoded strings of the images.
        image_urls (List[str]): A list of URLs for images to be processed.

    Returns:
        Tuple[Optional[List[ImageAltText]], Optional[str]]: A tuple containing a list of ImageAltText objects and an optional tracing URL.
        The first element is a list of alt texts and titles for each image, or None if the operation fails.
        The second element is a URL to trace the operation, or None if tracing is disabled or fails.
    """
    llm = determine_llm()

    content = [
        {
            "type": "text",
            "text": f"""ARTICLE: {input_text}"""
        }
    ]

    # Process images and add to content
    for image_name, base64_string in images.items():
        mime_type, _ = mimetypes.guess_type(image_name)
        if not mime_type:
            logging.warning(f"Could not determine MIME type for image: {image_name}")
            continue

        # Check if the MIME type is SVG, convert to PNG if true
        if mime_type == "image/svg+xml":
            logging.info(f"Converting SVG to PNG for image: {image_name}")
            svg_data = base64.b64decode(base64_string)
            base64_string = svg_to_png_base64(svg_data)
            mime_type = "image/png"

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
                content="You are a world-class expert at generating concise alternative text and title attributes for images defined in technical articles written in markdown format.\nFor each image in the article use a contextual understanding of the article text and the image itself to generate a concise alternative text and title attribute.\n{format_instructions}".format(format_instructions=parser.get_format_instructions())),
            HumanMessage(content=content),
            HumanMessage(
                content=f"Tip: List of file names of images including their paths or URLs: {str(all_image_identifiers)}"
            ),
        ]
    )

    alttexts = None
    run_url = None

    if os.getenv("LANGFUSE_TRACING", "False"):
        alttexts = llm.invoke(messages.format_messages(), config={"callbacks": [langfuse_handler]})
        run_url = str(langfuse_handler.get_trace_url())
    else:
        alttexts = llm.invoke(messages.format_messages())

    if alttexts:
        try:
            alttexts_parsed = parser.parse(alttexts.content)
            return alttexts_parsed, run_url
        except Exception as e:
            logging.error(f"Error parsing LLM response: {str(e)}")

    return None, run_url