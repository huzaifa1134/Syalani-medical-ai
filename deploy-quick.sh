#!/bin/bash

# =============================================================================
# Quick Deploy Script - For updating existing deployment
# =============================================================================
# This script quickly rebuilds and redeploys the application
# using existing environment variables
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE_NAME="whatsapp-ai-assistant"
REGION="us-central1"

echo -e "${BLUE}Quick Deploy - Rebuilding and Redeploying${NC}"
echo ""

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo "Error: No project set"
    exit 1
fi

echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"
echo ""

# Build
echo -e "${BLUE}Building container...${NC}"
gcloud builds submit --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" .

# Deploy
echo ""
echo -e "${BLUE}Deploying to Cloud Run...${NC}"
gcloud run deploy "$SERVICE_NAME" \
    --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
    --region "$REGION" \
    --platform managed

# Get URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format="value(status.url)")

echo ""
echo -e "${GREEN}✓ Deployment completed!${NC}"
echo ""
echo "Service URL: $SERVICE_URL"
echo "Webhook URL: $SERVICE_URL/api/v1/webhook"
echo "Health Check: $SERVICE_URL/api/v1/health"
echo ""
echo "Test deployment:"
echo "  curl $SERVICE_URL/api/v1/health"
echo ""
