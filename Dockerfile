FROM public.ecr.aws/lambda/python:3.11

COPY pyproject.toml ./
RUN pip install --no-cache-dir . 2>/dev/null || pip install --no-cache-dir \
    boto3>=1.34.0 \
    aioboto3>=12.0.0 \
    pydantic>=2.5.0 \
    "pyjwt[crypto]>=2.8.0" \
    python-dateutil>=2.8.2 \
    requests>=2.31.0

COPY src/ ./src/

CMD ["src.interfaces.websocket_handlers.connect.handler"]
