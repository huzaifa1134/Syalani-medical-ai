#!/bin/bash

# =============================================================================
# Update Environment Variables on Google Cloud Run
# =============================================================================
# This script updates environment variables for an already deployed service
# without redeploying the entire application.
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE_NAME="whatsapp-ai-assistant"
REGION="us-central1"

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

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_header "Update Cloud Run Environment Variables"

# Check if service exists
if ! gcloud run services describe "$SERVICE_NAME" --region "$REGION" &>/dev/null; then
    print_error "Service '$SERVICE_NAME' not found in region '$REGION'"
    echo "Please deploy the service first using deploy.sh"
    exit 1
fi

print_success "Service found: $SERVICE_NAME"
echo ""

# Menu for update options
echo "What would you like to update?"
echo "1) Update single environment variable"
echo "2) Update multiple environment variables"
echo "3) Update from .env file"
echo "4) Show current environment variables"
echo "5) Exit"
echo ""
read -p "Select option (1-5): " option

case $option in
    1)
        print_info "Update single environment variable"
        read -p "Variable name: " var_name
        read -p "Variable value: " var_value

        print_info "Updating $var_name..."
        gcloud run services update "$SERVICE_NAME" \
            --region "$REGION" \
            --update-env-vars "$var_name=$var_value"

        print_success "Updated $var_name"
        ;;

    2)
        print_info "Update multiple environment variables"
        echo "Enter environment variables in format: KEY1=value1,KEY2=value2"
        read -p "Variables: " env_vars

        print_info "Updating environment variables..."
        gcloud run services update "$SERVICE_NAME" \
            --region "$REGION" \
            --update-env-vars "$env_vars"

        print_success "Environment variables updated"
        ;;

    3)
        if [ ! -f .env ]; then
            print_error ".env file not found"
            exit 1
        fi

        print_info "Reading .env file..."

        # Parse .env file and build env vars string
        ENV_VARS=""
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ $key =~ ^#.*$ ]] && continue
            [[ -z $key ]] && continue

            # Remove quotes from value
            value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")

            if [ -z "$ENV_VARS" ]; then
                ENV_VARS="$key=$value"
            else
                ENV_VARS="$ENV_VARS,$key=$value"
            fi
        done < .env

        if [ -z "$ENV_VARS" ]; then
            print_error "No valid environment variables found in .env"
            exit 1
        fi

        print_info "Updating environment variables from .env..."
        gcloud run services update "$SERVICE_NAME" \
            --region "$REGION" \
            --update-env-vars "$ENV_VARS"

        print_success "Environment variables updated from .env"
        ;;

    4)
        print_info "Current environment variables:"
        echo ""
        gcloud run services describe "$SERVICE_NAME" \
            --region "$REGION" \
            --format="json" | \
            jq -r '.spec.template.spec.containers[0].env[] | "\(.name)=\(.value)"'
        ;;

    5)
        print_info "Exiting..."
        exit 0
        ;;

    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

echo ""
print_success "Operation completed successfully!"
