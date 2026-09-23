# Glama (and other directory checkers) run the server in a container and only need it to start
# and answer MCP introspection. Introspection is answered locally by the bridge, so this image
# needs no egress and no credentials to pass. Real tool calls are forwarded to the hosted endpoint.
FROM python:3.12-slim
WORKDIR /app
COPY src/100pro_mcp.py /app/100pro_mcp.py
ENTRYPOINT ["python3", "/app/100pro_mcp.py"]
