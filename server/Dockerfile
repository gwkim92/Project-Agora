FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt

COPY server /app/server
COPY openapi.yaml /app/openapi.yaml
COPY llms.txt /app/llms.txt
COPY agora-agent-manifest.json /app/agora-agent-manifest.json
COPY agents.json /app/agents.json
COPY .well-known /app/.well-known
COPY docs /app/docs

EXPOSE 8000

# Entrypoint runs Alembic migrations when DATABASE_URL is set.
COPY server/entrypoint.sh /app/server/entrypoint.sh
RUN chmod +x /app/server/entrypoint.sh

# Production-ish default: single process, multiple workers via uvicorn.
# If you prefer gunicorn, add it to requirements and swap the CMD.
ENTRYPOINT ["/app/server/entrypoint.sh"]
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]

