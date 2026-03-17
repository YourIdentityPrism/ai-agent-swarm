FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN playwright install chromium

COPY browser_bot.py /app/browser_bot.py
COPY bot_config.json /app/bot_config.json
COPY ai_agent/ /app/ai_agent/

VOLUME ["/app/profiles", "/app/logs"]

CMD ["python", "browser_bot.py"]
