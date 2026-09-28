FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN python -c "from pathlib import Path; p = Path('/tmp/requirements.txt'); p.write_text(p.read_text(encoding='utf-8-sig'), encoding='utf-8')" \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app

EXPOSE 8000
