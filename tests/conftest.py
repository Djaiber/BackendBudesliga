"""Root conftest — set required env vars before any src module is imported.

This file is loaded by pytest before test collection, so env vars are in place
when src/main.py runs build_container() at module level.
"""

import os

_TEST_ENV: dict[str, str] = {
    "AWS_REGION": "eu-central-1",
    "AWS_ACCOUNT_ID": "123456789012",
    "DYNAMODB_TABLE": "test-table",
    "EVENT_BUS_NAME": "test-bus",
    "S3_REPLAY_BUCKET": "test-bucket",
    "BEDROCK_MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0",
    "BEDROCK_REGION": "us-east-1",
    "COGNITO_USER_POOL_ID": "eu-central-1_TestPool",
    "COGNITO_APP_CLIENT_ID": "testclient123",
    "COGNITO_REGION": "eu-central-1",
    "REPLAY_DATA_PATH": "/tmp/test-replay",
    "CLOSEST_PREDICTION_POINTS": "50,25,10",
    "ACCEPT_ANY_TOKEN": "true",
}

for _key, _value in _TEST_ENV.items():
    os.environ.setdefault(_key, _value)
