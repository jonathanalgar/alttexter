import argparse
import json
import logging
import logging.config
import os
import ssl
from pathlib import Path

import uvicorn
from fastapi import Body, Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader

from alttexter import alttexter
from preprocessing import is_valid_notebook, remove_outputs_from_notebook
from schema import (AlttexterRequest, ErrorResponse, ExtendedAlttexterResponse,
                    handle_endpoint_error)

# --------------------------------
# Configuration and initialization
# --------------------------------

app = FastAPI(
    title="alttexter",
    description="`gpt4-vision-preview` wrapper service to batch generate alternative ('alt') text and title attributes for images defined in markdown formatted files.",
    version="0.1",
    cookies_secure=True
)

with open('config.json') as f:
    config = json.load(f)

logging.basicConfig(
    level=config['logging']['level'],
    format=config['logging']['format'],
    datefmt=config['logging']['datefmt']
)

# Command-line arguments for SSL and server configuration
parser = argparse.ArgumentParser(description="Run a FastAPI server with SSL")
parser.add_argument("--certfile", type=str, required=True, help="Path to the SSL certificate file")
parser.add_argument("--keyfile", type=str, required=True, help="Path to the private key file associated with the SSL certificate")
parser.add_argument("--host", type=str, default="localhost", help="Host to bind the service to")
parser.add_argument("--port", type=int, default=9004, help="Port to bind the service to")

args = parser.parse_args()

# --------------------------------
# Authentication and middleware
# --------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=config['cors']['config']['allow_origins'],
    allow_credentials=config['cors']['config']['allow_credentials'],
    allow_methods=config['cors']['config']['allow_methods'],
    allow_headers=config['cors']['config']['allow_headers'],
    expose_headers=config['cors']['config']['expose_headers'],
)


@app.middleware("http")
async def secure_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in config['security']['headers'].items():
        response.headers[header] = value
    return response

API_KEY_NAME = "X-API-Token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False, description='API key required for authorization')


async def get_api_key(api_key: str = Security(api_key_header)):
    correct_api_key = os.getenv("ALTTEXTER_TOKEN")
    if api_key != correct_api_key:
        raise HTTPException(status_code=401, detail="Invalid API Token")
    return api_key

# --------------------------------
# Route
# --------------------------------


@app.post(
    "/alttexter",
    response_model=ExtendedAlttexterResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)
def alttexter_text(
    request: AlttexterRequest = Body(...),
    token: str = Depends(get_api_key)
):
    """Endpoint to process alttexter requests."""
    try:
        text = request.text
        images = request.images
        image_urls = request.image_urls

        # Preprocessing
        if (is_valid_notebook(text)):
            text = remove_outputs_from_notebook(text)

        alttexts_response, run_url = alttexter(text, images, image_urls)
        if alttexts_response is None:
            raise Exception("Failed to generate alt texts. Please try again later.")

        return ExtendedAlttexterResponse(images=alttexts_response.images, run_url=run_url)

    except Exception as e:
        handle_endpoint_error(e)

# --------------------------------
# Check files and run service
# --------------------------------


def check_file_exists(file_path: str, file_type: str):
    """Ensures the SSL certificate and key files exist."""
    if not Path(file_path).exists():
        error_message = f"{file_type} '{file_path}' does not exist."
        logging.error(error_message)
        raise SystemExit(1)


if __name__ == "__main__":
    check_file_exists(args.certfile, "SSL certificate file")
    check_file_exists(args.keyfile, "Private key file")

    CERT_FILE = args.certfile
    KEY_FILE = args.keyfile

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(os.path.expanduser(CERT_FILE), keyfile=os.path.expanduser(KEY_FILE))

    # Run the Uvicorn server with SSL configuration
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        ssl_certfile=os.path.expanduser(CERT_FILE),
        ssl_keyfile=os.path.expanduser(KEY_FILE),
    )
