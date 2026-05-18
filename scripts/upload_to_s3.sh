#!/bin/bash
#
# Upload converted replay data to S3
#
# Usage: ./scripts/upload_to_s3.sh [bucket-name]
#
# Environment variables:
#   S3_REPLAY_BUCKET - S3 bucket name (default: bundesliga-replay-data)
#   AWS_REGION - AWS region (default: eu-central-1)

set -e

# Configuration
BUCKET_NAME="${1:-${S3_REPLAY_BUCKET:-bundesliga-replay-data}}"
AWS_REGION="${AWS_REGION:-eu-central-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"

echo "=========================================="
echo "Upload Replay Data to S3"
echo "=========================================="
echo "Bucket: ${BUCKET_NAME}"
echo "Region: ${AWS_REGION}"
echo ""

# Check if output files exist
if [ ! -d "${OUTPUT_DIR}" ]; then
    echo "ERROR: Output directory not found: ${OUTPUT_DIR}"
    echo "Run 'make convert-xml' first to generate the JSON files"
    exit 1
fi

REQUIRED_FILES=("events.json" "match_info.json" "kpi.json")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "${OUTPUT_DIR}/${file}" ]; then
        echo "ERROR: Required file not found: ${OUTPUT_DIR}/${file}"
        echo "Run 'make convert-xml' first to generate the JSON files"
        exit 1
    fi
done

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI is not installed"
    echo "Install it from: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if bucket exists, create if not
echo "Checking if bucket exists..."
if ! aws s3 ls "s3://${BUCKET_NAME}" --region "${AWS_REGION}" 2>/dev/null; then
    echo "Bucket does not exist. Creating..."
    aws s3 mb "s3://${BUCKET_NAME}" --region "${AWS_REGION}"
    echo "✓ Bucket created"
else
    echo "✓ Bucket exists"
fi

# Upload files
echo ""
echo "Uploading files..."

for file in "${REQUIRED_FILES[@]}"; do
    echo "  Uploading ${file}..."
    aws s3 cp "${OUTPUT_DIR}/${file}" "s3://${BUCKET_NAME}/${file}" \
        --region "${AWS_REGION}" \
        --content-type "application/json"
    echo "  ✓ ${file} uploaded"
done

echo ""
echo "=========================================="
echo "Upload complete!"
echo "=========================================="
echo ""
echo "Files available at:"
for file in "${REQUIRED_FILES[@]}"; do
    echo "  s3://${BUCKET_NAME}/${file}"
done
echo ""
