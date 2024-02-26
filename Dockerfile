FROM python:3.11-slim AS base
WORKDIR /app
COPY requirements.txt .

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    libcairo2 \
    libcairo2-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "main.py"]