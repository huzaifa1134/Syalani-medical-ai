#!/bin/bash

# =============================================================================
# WhatsApp AI Assistant - Google Cloud Run Deployment Script
# =============================================================================
# This script deploys the application to Google Cloud Run with all required
# environment variables and configurations.
#
# Prerequisites:
# 1. Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install
# 2. Authenticate: gcloud auth login
# 3. Set project: gcloud config set project YOUR_PROJECT_ID
# 4. Enable APIs:
#    - Cloud Run API
#    - Cloud Build API
#    - Container Registry API
#    - Artifact Registry API (optional)
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="whatsapp-ai-assistant"
REGION="us-central1"
MEMORY="1Gi"
CPU="1"
MAX_INSTANCES="10"
MIN_INSTANCES="0"
TIMEOUT="300"

# =============================================================================
# Functions
# =============================================================================

print_header() {
    echo -e "${BLUE}=============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=============================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# =============================================================================
# Pre-flight Checks
# =============================================================================

print_header "Pre-flight Checks"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it from:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi
print_success "gcloud CLI is installed"

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    print_error "Not logged in to gcloud. Please run: gcloud auth login"
    exit 1
fi
print_success "Authenticated with gcloud"

# Get current project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    print_error "No project set. Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi
print_success "Project ID: $PROJECT_ID"

# Check if required APIs are enabled
print_info "Checking required APIs..."
REQUIRED_APIS=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "containerregistry.googleapis.com"
    "speech.googleapis.com"
    "texttospeech.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        print_success "API enabled: $api"
    else
        print_warning "API not enabled: $api"
        print_info "Enabling $api..."
        gcloud services enable "$api"
        print_success "Enabled $api"
    fi
done

# =============================================================================
# Environment Variables Setup
# =============================================================================

print_header "Environment Variables Configuration"

print_warning "You need to provide the following environment variables."
print_info "These will be set as Cloud Run environment variables (secrets should use Secret Manager)."
echo ""

# Function to prompt for environment variable
prompt_env_var() {
    local var_name=$1
    local var_description=$2
    local is_secret=$3
    local current_value=$4

    if [ -n "$current_value" ]; then
        echo -e "${YELLOW}$var_name${NC} ($var_description)"
        echo -e "Current value: ${BLUE}${current_value:0:20}...${NC}"
        read -p "Keep current value? (Y/n): " keep
        if [[ $keep =~ ^[Nn]$ ]]; then
            if [ "$is_secret" = "true" ]; then
                read -sp "Enter new value: " value
                echo ""
            else
                read -p "Enter new value: " value
            fi
            echo "$value"
        else
            echo "$current_value"
        fi
    else
        echo -e "${YELLOW}$var_name${NC} ($var_description)"
        if [ "$is_secret" = "true" ]; then
            read -sp "Enter value: " value
            echo ""
        else
            read -p "Enter value: " value
        fi
        echo "$value"
    fi
}

# Load existing .env if it exists
if [ -f .env ]; then
    print_info "Loading existing .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Collect environment variables
echo ""
print_info "Please provide the following configuration values:"
echo ""

MONGODB_URI=$(prompt_env_var "MONGODB_URI" "MongoDB Atlas connection string" "true" "${MONGODB_URI:-}")
GEMINI_API_KEY=$(prompt_env_var "GEMINI_API_KEY" "Google Gemini API key" "true" "${GEMINI_API_KEY:-}")
WABA_API_URL=$(prompt_env_var "WABA_API_URL" "WhatsApp Business API URL" "false" "${WABA_API_URL:-https://graph.facebook.com/v18.0}")
WABA_PHONE_NUMBER_ID=$(prompt_env_var "WABA_PHONE_NUMBER_ID" "WhatsApp Phone Number ID" "false" "${WABA_PHONE_NUMBER_ID:-}")
WABA_ACCESS_TOKEN=$(prompt_env_var "WABA_ACCESS_TOKEN" "WhatsApp Access Token" "true" "${WABA_ACCESS_TOKEN:-}")
WABA_VERIFY_TOKEN=$(prompt_env_var "WABA_VERIFY_TOKEN" "WhatsApp Verify Token" "true" "${WABA_VERIFY_TOKEN:-}")
GCP_PROJECT_ID=$(prompt_env_var "GCP_PROJECT_ID" "GCP Project ID for STT/TTS" "false" "${GCP_PROJECT_ID:-$PROJECT_ID}")

# Redis configuration
echo ""
print_info "Redis Configuration (use managed Redis or Cloud Memorystore)"
REDIS_HOST=$(prompt_env_var "REDIS_HOST" "Redis host address" "false" "${REDIS_HOST:-}")
REDIS_PORT=$(prompt_env_var "REDIS_PORT" "Redis port" "false" "${REDIS_PORT:-6379}")
REDIS_PASSWORD=$(prompt_env_var "REDIS_PASSWORD" "Redis password (leave empty if none)" "true" "${REDIS_PASSWORD:-}")

# =============================================================================
# Build and Deploy
# =============================================================================

print_header "Building and Deploying to Cloud Run"

# Build the container
print_info "Building Docker container..."
gcloud builds submit \
    --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
    --timeout=20m \
    .

print_success "Container built successfully"

# Deploy to Cloud Run
print_info "Deploying to Cloud Run..."

# Prepare environment variables string
ENV_VARS="ENV=production,DEBUG=false,LOG_LEVEL=INFO"
ENV_VARS="$ENV_VARS,APP_NAME=WhatsApp Voice AI"
ENV_VARS="$ENV_VARS,API_VERSION=v1"
ENV_VARS="$ENV_VARS,HOST=0.0.0.0"
ENV_VARS="$ENV_VARS,PORT=8080"
ENV_VARS="$ENV_VARS,MONGODB_URI=$MONGODB_URI"
ENV_VARS="$ENV_VARS,MONGODB_DB_NAME=healthcare_ai"
ENV_VARS="$ENV_VARS,MONGODB_COLLECTION=doctors"
ENV_VARS="$ENV_VARS,MONGODB_VECTOR_COLLECTION=treatment_protocols"
ENV_VARS="$ENV_VARS,REDIS_HOST=$REDIS_HOST"
ENV_VARS="$ENV_VARS,REDIS_PORT=$REDIS_PORT"
ENV_VARS="$ENV_VARS,REDIS_DB=0"
ENV_VARS="$ENV_VARS,REDIS_PASSWORD=$REDIS_PASSWORD"
ENV_VARS="$ENV_VARS,CONTEXT_TTL=1800"
ENV_VARS="$ENV_VARS,GCP_PROJECT_ID=$GCP_PROJECT_ID"
ENV_VARS="$ENV_VARS,GCP_STT_LANGUAGE=ur-PK"
ENV_VARS="$ENV_VARS,GCP_TTS_LANGUAGE=ur-PK"
ENV_VARS="$ENV_VARS,GCP_TTS_VOICE_NAME=ur-PK-Standard-A"
ENV_VARS="$ENV_VARS,GEMINI_API_KEY=$GEMINI_API_KEY"
ENV_VARS="$ENV_VARS,GEMINI_MODEL=gemini-1.5-flash"
ENV_VARS="$ENV_VARS,WABA_API_URL=$WABA_API_URL"
ENV_VARS="$ENV_VARS,WABA_PHONE_NUMBER_ID=$WABA_PHONE_NUMBER_ID"
ENV_VARS="$ENV_VARS,WABA_ACCESS_TOKEN=$WABA_ACCESS_TOKEN"
ENV_VARS="$ENV_VARS,WABA_VERIFY_TOKEN=$WABA_VERIFY_TOKEN"
ENV_VARS="$ENV_VARS,MAX_MESSAGES_PER_USER=10"
ENV_VARS="$ENV_VARS,RATE_LIMIT_WINDOW=60"

gcloud run deploy "$SERVICE_NAME" \
    --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --memory "$MEMORY" \
    --cpu "$CPU" \
    --timeout "$TIMEOUT" \
    --max-instances "$MAX_INSTANCES" \
    --min-instances "$MIN_INSTANCES" \
    --set-env-vars "$ENV_VARS"

print_success "Deployment completed!"

# =============================================================================
# Post-deployment Information
# =============================================================================

print_header "Deployment Information"

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format="value(status.url)")

echo ""
print_success "Service deployed successfully!"
echo ""
echo -e "${GREEN}Service URL:${NC} $SERVICE_URL"
echo -e "${GREEN}Webhook URL:${NC} $SERVICE_URL/api/v1/webhook"
echo -e "${GREEN}Health Check:${NC} $SERVICE_URL/api/v1/health"
echo ""

print_header "Next Steps"
echo ""
echo "1. Configure WhatsApp Webhook:"
echo "   - Go to Meta Developer Portal"
echo "   - Set webhook URL: $SERVICE_URL/api/v1/webhook"
echo "   - Set verify token: $WABA_VERIFY_TOKEN"
echo ""
echo "2. Test the deployment:"
echo "   curl $SERVICE_URL/api/v1/health"
echo ""
echo "3. Monitor logs:"
echo "   gcloud run services logs tail $SERVICE_NAME --region $REGION"
echo ""
echo "4. View service details:"
echo "   gcloud run services describe $SERVICE_NAME --region $REGION"
echo ""

print_success "Deployment script completed successfully!"
