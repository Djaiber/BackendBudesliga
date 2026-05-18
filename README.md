# BackendBudes — Connected Arena Backend

Real-time multiplayer prediction game backend for live football matches, built with AWS serverless architecture and hexagonal design.

## Architecture

Hexagonal (Ports & Adapters) architecture with strict separation:
- **Domain layer**: Pure business logic, zero AWS dependencies
- **Application layer**: Use cases orchestrating domain services
- **Infrastructure layer**: AWS adapters (DynamoDB, EventBridge, Bedrock, API Gateway WebSocket)
- **Interfaces layer**: Lambda handlers (thin entry points)

## Tech Stack

- **Language**: Python 3.11
- **Runtime**: AWS Lambda
- **API**: AWS API Gateway WebSocket
- **Events**: Amazon EventBridge
- **Data**: Amazon DynamoDB
- **AI**: Amazon Bedrock (Claude Haiku)
- **Storage**: Amazon S3
- **Local dev**: pytest, moto, localstack

## Prerequisites

- Python 3.11
- AWS CLI configured (for deployment)
- Docker (for local testing with localstack)

## Setup

```bash
# Install dependencies
make install

# Copy environment template
cp .env.example .env

# Edit .env with your AWS settings
```

## Development

```bash
# Run tests
make test

# Type checking
make typecheck

# Linting
make lint

# Format code
make format

# Run all checks
make check
```

## Data Pipeline

### Convert XML datasets to JSON

```bash
# Convert XML match data to normalized JSON
make convert-xml

# Output files created in scripts/output/:
# - events.json (match events sorted by time)
# - match_info.json (teams, lineups, metadata)
# - kpi.json (KPI snapshots by minute)
```

### Upload to S3

```bash
# Upload converted data to S3 bucket
./scripts/upload_to_s3.sh
```

## Local Development

### Run replay engine locally (no AWS)

```bash
# Streams match events to stdout at configured speed
make run-local-replay

# Or directly:
python scripts/run_local_replay.py
```

### Run with localstack (full AWS simulation)

```bash
# Start localstack services
docker-compose up -d

# Run integration tests
make test-integration

# Stop services
docker-compose down
```

## Project Structure

```
src/
├── domain/              # Pure business logic (no AWS imports)
│   ├── entities/        # Business objects
│   ├── services/        # Domain logic
│   └── ports/           # Abstract interfaces (Protocols)
├── application/         # Use cases (orchestration)
│   ├── use_cases/
│   └── dto/
├── infrastructure/      # AWS adapters (boto3 lives here)
│   ├── websocket/
│   ├── dynamodb/
│   ├── eventbridge/
│   ├── ai/
│   ├── replay/
│   └── s3/
└── interfaces/          # Lambda handlers (entry points)
    ├── websocket_handlers/
    └── event_handlers/

scripts/                 # Utilities
tests/                   # Test suite
```

## WebSocket Contract

### Client → Server

```json
{ "type": "JOIN_ROOM" }
{ "type": "SUBMIT_PREDICTION", "windowId": "...", "value": "..." }
{ "type": "EMOJI", "emoji": "🔥" }
{ "type": "PING" }
```

### Server → Client

```json
{ "type": "ROOM_JOINED", "roomId": "...", "players": [...] }
{ "type": "PREDICTION_WINDOW_OPEN", "windowId": "...", "prompt": "...", ... }
{ "type": "PREDICTION_RESULT", "windowId": "...", "winners": [...], ... }
{ "type": "MATCH_EVENT", "minute": 45, "eventType": "GOAL", ... }
{ "type": "LEADERBOARD_UPDATE", "entries": [...] }
```

## Domain Rules

### Rooms
- 3-4 players per room
- Rooms with <3 players merge automatically
- Max 25 fans in leaderboard merge window

### Scoring
- Exact prediction: 100 points
- Closest non-exact: 50, 30, 20, 10 (descending)
- No response: -10 penalty
- Speed multiplier: up to x1.1

### Streaks
- 3 correct → x1.2 multiplier
- 5 correct → x1.5 multiplier
- Wrong answer resets streak

### Tiers (by EXP)
- Dummies: 0-400
- Enthusiast: 401-700
- Amateur: 701-900
- Savvy: 901-1200

## Environment Variables

See `.env.example` for all configuration options.

Key variables:
- `DYNAMODB_TABLE`: DynamoDB table name
- `REPLAY_SPEED`: Match speed multiplier (60 = 1 match min = 1 real sec)
- `BEDROCK_MODEL_ID`: Bedrock model identifier
- `S3_REPLAY_BUCKET`: S3 bucket for replay data
- `WEBSOCKET_API_ENDPOINT`: API Gateway WebSocket endpoint

## Deployment

Deployment is handled by the **InfraBudes** repository using Terraform.

This repository provides the Lambda function code and dependencies.

## Testing

```bash
# Unit tests (domain + application layers)
pytest tests/unit/

# Integration tests (with moto mocks)
pytest tests/integration/

# All tests with coverage
pytest --cov=src --cov-report=html
```

## Cost Control

- Bedrock called max once per prediction window
- Prompt caching target: ≥60% hit rate
- CloudWatch alarm: bedrock_invocations_per_match > 100

## License

MIT
