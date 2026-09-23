# Directory checkers (Glama, and any other registry that builds the repo) start this image and only
# need the server to start and answer MCP introspection. Introspection (initialize / tools/list) is
# answered locally by the bridge, so the container needs no egress, no credentials and no deps to
# pass the check. Real tool calls are forwarded to the hosted x402 endpoint.
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY pro100 /app/pro100
COPY 100pro_mcp.py /app/100pro_mcp.py
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/app/100pro_mcp.py"]
