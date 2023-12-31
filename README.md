# alttexter

![ci](https://github.com/jonathanalgar/alttexter/actions/workflows/build-docker.yml/badge.svg)

![License: GPLv3](https://img.shields.io/badge/license-GPLv3-blue) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://makeapullrequest.com)

## Overview

`gpt4-vision-preview` wrapper service to batch generate alternative ('alt') text and title attributes for images defined in markdown formatted files.

Exists to abstract interaction with the OpenAI and LangSmith APIs and provides a single interface for clients. Currently there is [alttexter-ghclient](https://github.com/jonathanalgar/alttexter-ghclient) but I'm excited about building for VSC too.

See OpenAPI specification for the service [here](https://app.swaggerhub.com/apis/JONATHANALGARGITHUB/alttexter/0.1).

### Why?

via [gov.uk:](https://design102.blog.gov.uk/2022/01/14/whats-the-alternative-how-to-write-good-alt-text/)

> When uploading images and visuals online, or in documents shared digitally, adding alt text can help people using assistive technologies to 'hear' those visuals. We aim to make sure that anyone using alt text through assistive technologies can get the same information from the description of an image as someone who relies on the visuals. Alt text often assists visually impaired people but is also used for search engine optimisation and for making sense of an image if it isn't visible or doesn't load. 

I was surprised how many prominent open-source projects have poor alt-text coverage across their docs.

## Usage

1. Clone the repo.
1. Copy `.env-example` to `.env` and fill in the required env variables.
1. Optionally edit `config.json` to customize CORS and logging.
1. Run `docker-compose up` to build and start the service.
1. Run `python client-example.py example/apis.ipynb` to test. Expected output:

    ```python
    $ python client-example.py example/apis.ipynb
    Enter endpoint URL (eg. https://alttexter-prod.westeurope.cloudapp.azure.com:9100/alttexter):
    Enter ALTTEXTER_TOKEN:
    INFO [30-12-2023 07:32:33] File read successfully.
    INFO [30-12-2023 07:32:33] Unsupported image type: https://colab.research.google.com/assets/colab-badge.svg
    INFO [30-12-2023 07:32:33] Encoded image: api_use_case.png
    INFO [30-12-2023 07:32:33] Encoded image: api_function_call.png
    INFO [30-12-2023 07:32:33] Payload Summary:
    INFO [30-12-2023 07:32:33] Total local images (encoded): 2
    INFO [30-12-2023 07:32:33] Total image URLs: 2
    INFO [30-12-2023 07:32:33] Image URLs: ['https://github.com/langchain-ai/langchain/blob/b9636e5c987e1217afcdf83e9c311568ad50c304/docs/static/img/api_chain.png?raw=true', 'https://github.com/langchain-ai/langchain/blob/b9636e5c987e1217afcdf83e9c311568ad50c304/docs/static/img/api_chain_response.png?raw=true']
    INFO [30-12-2023 07:32:33] Sending payload to alttexter...
    INFO [30-12-2023 07:32:46] Response received at 30-12-2023 07:32:46
    {"images":[{"name":"api_use_case.png","title":"API Use Case Diagram","alt_text":"Diagram illustrating the use case of an LLM interacting with an external API."},{"name":"api_function_call.png","title":"API Function Call Process","alt_text":"Flowchart showing the process of an LLM formulating an API call based on a user query."},{"name":"https://github.com/langchain-ai/langchain/blob/b9636e5c987e1217afcdf83e9c311568ad50c304/docs/static/img/api_chain.png?raw=true","title":"API Request Chain Trace","alt_text":"Screenshot of a LangSmith trace showing the API request chain for generating an API URL."},{"name":"https://github.com/langchain-ai/langchain/blob/b9636e5c987e1217afcdf83e9c311568ad50c304/docs/static/img/api_chain_response.png?raw=true","title":"API Response Chain Trace","alt_text":"Screenshot of a LangSmith trace showing the API response chain for providing a natural language answer."}],"run_url":"https://smith.langchain.com/public/7596e591-559d-4ba4-b35e-58f93db6d25d/r"}

    ```
    
1. This is a very basic client. Check [alttexter-ghclient](https://github.com/jonathanalgar/alttexter-ghclient) to integrate the service into your docs-as-code pipeline.

## Features

* Uses LangChain's [Pydantic parser](https://python.langchain.com/docs/modules/model_io/output_parsers/pydantic) as foundation for system prompt to reliably generate a JSON of expected format ([function calling](https://community.openai.com/t/does-the-model-gpt-4-vision-preview-have-function-calling/490197/2) will be even cooler).
* Optionally integrates with LangSmith (in beta) to serve [trace URL](https://docs.smith.langchain.com/tracing/tracing-faq) for each generation.

## TODO

- [ ] Special handling for large files and images.
- [ ] Rate limiting at the service level.
- [ ] Option to use [Azure OpenAI Services](https://techcommunity.microsoft.com/t5/ai-azure-ai-services-blog/gpt-4-turbo-with-vision-is-now-available-on-azure-openai-service/ba-p/4008456).
- [ ] Explore extending to multimodal models beyond OpenAI.
- [ ] Extend this TODO list