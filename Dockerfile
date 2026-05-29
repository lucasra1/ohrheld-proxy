FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY https_proxy.py /app/https_proxy.py

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["python", "/app/https_proxy.py", "--host", "0.0.0.0", "--port", "8080", "--log", "/tmp/proxy-log.jsonl"]
