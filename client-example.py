import argparse
import base64
import getpass
import json
import logging
import os
import re
from datetime import datetime

import requests
import urllib3

logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s [%(asctime)s] %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S')

SUPPORTED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp')


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def extract_images_from_markdown(md_content):
    pattern = r'!\[(.*?)\]\((.*?)\s*(?:\"(.*?)\")?\)'
    images = re.findall(pattern, md_content)
    local_images = {}
    image_urls = []

    for alt_text, image_path, _ in images:
        _, ext = os.path.splitext(image_path.split('?')[0])
        if image_path.startswith(('http://', 'https://')) and ext.lower() in SUPPORTED_IMAGE_EXTENSIONS:
            image_urls.append(image_path)
        elif ext.lower() in SUPPORTED_IMAGE_EXTENSIONS:
            local_images[image_path] = None
        else:
            logging.info(f"Unsupported image type: {image_path}")

    return local_images, image_urls


def encode_local_images(images, base_dir):
    for image_path in images:
        full_image_path = os.path.join(base_dir, image_path)
        if os.path.exists(full_image_path):
            images[image_path] = encode_image(full_image_path)
            logging.info(f"Encoded image: {image_path}")
        else:
            logging.warning(f"Image not found or unsupported: {full_image_path}")


def log_full_payload(md_content, encoded_images, image_urls):
    encoded_images_summary = {k: "<base64-encoded-data>" for k in encoded_images.keys()}
    payload = {
        "text": md_content,
        "images": encoded_images_summary,
        "image_urls": image_urls
    }
    logging.info("Complete Payload (with base64 placeholders):")
    logging.info(json.dumps(payload, indent=2))


def log_payload_summary(encoded_images, image_urls):
    logging.info("Payload Summary:")
    logging.info(f"Total local images (encoded): {len(encoded_images)}")
    logging.info(f"Total image URLs: {len(image_urls)}")
    if len(image_urls) > 0:
        logging.info(f"Image URLs: {image_urls}")


def send_file_to_api(md_content, encoded_images, image_urls, url, token, full_payload, verify_ssl=True):
    if full_payload:
        log_full_payload(md_content, encoded_images, image_urls)
    else:
        log_payload_summary(encoded_images, image_urls)

    actual_payload = json.dumps({
        "text": md_content,
        "images": encoded_images,
        "image_urls": image_urls
    })

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-API-Token": token
    }

    logging.info("Sending payload to alttexter...")
    try:
        response = requests.post(url, headers=headers, data=actual_payload, timeout=120, verify=verify_ssl)
        response.raise_for_status()  # Raises an HTTPError for bad responses
    except requests.exceptions.SSLError as ssl_err:
        if verify_ssl:
            logging.error(f"SSL Error occurred: {ssl_err}")
            raise
        else:
            logging.warning("SSL verification is disabled. Proceeding with insecure request.")
            response = requests.post(url, headers=headers, data=actual_payload, timeout=120, verify=False)
            response.raise_for_status()
    except requests.exceptions.RequestException as req_err:
        logging.error(f"An error occurred while sending the request: {req_err}")
        raise

    timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    logging.info(f"Response received at {timestamp}")

    return response.text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send markdown file to alttexter")
    parser.add_argument("md_file_path", help="Path to file containing markdown formatted text.")
    parser.add_argument("--full", action="store_true", help="Log the full payload instead of the summary")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL certificate verification")

    args = parser.parse_args()

    url = os.getenv("ALTTEXTER_CLIENT_EXAMPLE_URL")
    token = os.getenv("ALTTEXTER_CLIENT_EXAMPLE_TOKEN")

    if not url:
        url = getpass.getpass(prompt="Enter endpoint URL (eg. https://alttexter-prod.westeurope.cloudapp.azure.com:9100/alttexter): ")
    if not token:
        token = getpass.getpass(prompt="Enter ALTTEXTER_TOKEN: ")

    with open(args.md_file_path, 'r') as file:
        md_content = file.read()
    logging.info("File read successfully.")

    base_dir = os.path.dirname(args.md_file_path)
    local_images, image_urls = extract_images_from_markdown(md_content)
    encode_local_images(local_images, base_dir)

    verify_ssl = not args.no_verify_ssl
    try:
        response = send_file_to_api(md_content, local_images, image_urls, url, token, args.full, verify_ssl)
        print(response)
    except requests.exceptions.RequestException as e:
        logging.error(f"Error occurred: {e}")
        print(f"Failed to get a response from the server: {e}")