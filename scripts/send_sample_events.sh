#!/usr/bin/env bash
# Send sample events covering all major types to EventBridge
set -e

BUS_NAME="${EVENT_BUS_NAME:-connected-arena}"
REGION="${AWS_REGION:-eu-central-1}"

echo "Sending diverse events to $BUS_NAME..."

# Corner kick at 5'
aws events put-events --region "$REGION" --entries '[
  {
    "Source": "replay",
    "DetailType": "MatchEvent",
    "Detail": "{\"event_id\":\"evt-001\",\"minute\":5,\"second\":0,\"event_type\":\"CORNER_KICK\",\"team\":\"Bayern\",\"player\":null,\"x_position\":null,\"y_position\":null,\"metadata\":{}}",
    "EventBusName": "'"$BUS_NAME"'"
  }
]'

sleep 2

# Goal at 12'
aws events put-events --region "$REGION" --entries '[
  {
    "Source": "replay",
    "DetailType": "MatchEvent",
    "Detail": "{\"event_id\":\"evt-002\",\"minute\":12,\"second\":15,\"event_type\":\"GOAL\",\"team\":\"Bayern\",\"player\":\"Müller\",\"x_position\":16.5,\"y_position\":34.0,\"metadata\":{}}",
    "EventBusName": "'"$BUS_NAME"'"
  }
]'

sleep 2

# Yellow card at 18'
aws events put-events --region "$REGION" --entries '[
  {
    "Source": "replay",
    "DetailType": "MatchEvent",
    "Detail": "{\"event_id\":\"evt-003\",\"minute\":18,\"second\":30,\"event_type\":\"YELLOW\",\"team\":\"Dortmund\",\"player\":\"Reus\",\"x_position\":45.0,\"y_position\":50.0,\"metadata\":{}}",
    "EventBusName": "'"$BUS_NAME"'"
  }
]'

sleep 2

# Foul at 22'
aws events put-events --region "$REGION" --entries '[
  {
    "Source": "replay",
    "DetailType": "MatchEvent",
    "Detail": "{\"event_id\":\"evt-004\",\"minute\":22,\"second\":0,\"event_type\":\"FOUL\",\"team\":\"Bayern\",\"player\":null,\"x_position\":null,\"y_position\":null,\"metadata\":{}}",
    "EventBusName": "'"$BUS_NAME"'"
  }
]'

sleep 2

# Shot at 28'
aws events put-events --region "$REGION" --entries '[
  {
    "Source": "replay",
    "DetailType": "MatchEvent",
    "Detail": "{\"event_id\":\"evt-005\",\"minute\":28,\"second\":45,\"event_type\":\"SHOT\",\"team\":\"Dortmund\",\"player\":\"Haaland\",\"x_position\":18.0,\"y_position\":35.0,\"metadata\":{}}",
    "EventBusName": "'"$BUS_NAME"'"
  }
]'

sleep 2

# Substitution at 35'
aws events put-events --region "$REGION" --entries '[
  {
    "Source": "replay",
    "DetailType": "MatchEvent",
    "Detail": "{\"event_id\":\"evt-006\",\"minute\":35,\"second\":0,\"event_type\":\"SUB\",\"team\":\"Bayern\",\"player\":\"Sané\",\"x_position\":null,\"y_position\":null,\"metadata\":{}}",
    "EventBusName": "'"$BUS_NAME"'"
  }
]'

echo "✓ Sent 6 diverse events (CORNER_KICK, GOAL, YELLOW, FOUL, SHOT, SUB)"
