# =============================================================================
# WhatsApp AI Assistant - Google Cloud Run Deployment Script (PowerShell)
# =============================================================================
# This script deploys the application to Google Cloud Run with all required
# environment variables and configurations.
#
# Prerequisites:
# 1. Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install
# 2. Authenticate: gcloud auth login
# 3. Set project: gcloud config set project YOUR_PROJECT_ID
# =============================================================================

$ErrorActionPreference = "Stop"

# Configuration
$SERVICE_NAME = "whatsapp-ai-assistant"
$REGION = "us-central1"
$MEMORY = "1Gi"
$CPU = "1"
$MAX_INSTANCES = "10"
$MIN_INSTANCES = "0"
$TIMEOUT = "300"

# =============================================================================
# Functions
# =============================================================================

function Write-Header {
    param($Message)
    Write-Host "=============================================================================" -ForegroundColor Blue
    Write-Host $Message -ForegroundColor Blue
    Write-Host "=============================================================================" -ForegroundColor Blue
}

function Write-Success {
    param($Message)
    Write-Host "√ $Message" -ForegroundColor Green
}

function Write-ErrorMsg {
    param($Message)
    Write-Host "× $Message" -ForegroundColor Red
}

function Write-Warning {
    param($Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-Info {
    param($Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

# =============================================================================
# Pre-flight Checks
# =============================================================================

Write-Header "Pre-flight Checks"

# Check if gcloud is installed
try {
    $null = gcloud version
    Write-Success "gcloud CLI is installed"
} catch {
    Write-ErrorMsg "gcloud CLI is not installed. Please install it from:"
    Write-Host "https://cloud.google.com/sdk/docs/install"
    exit 1
}

# Check if logged in
try {
    $account = gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>&1
    if ($account) {
        Write-Success "Authenticated with gcloud"
    } else {
        Write-ErrorMsg "Not logged in to gcloud. Please run: gcloud auth login"
        exit 1
    }
} catch {
    Write-ErrorMsg "Not logged in to gcloud. Please run: gcloud auth login"
    exit 1
}

# Get current project
try {
    $PROJECT_ID = gcloud config get-value project 2>&1 | Select-Object -Last 1
    if (-not $PROJECT_ID) {
        Write-ErrorMsg "No project set. Please run: gcloud config set project YOUR_PROJECT_ID"
        exit 1
    }
    Write-Success "Project ID: $PROJECT_ID"
} catch {
    Write-ErrorMsg "Failed to get project ID"
    exit 1
}

# Check and enable required APIs
Write-Info "Checking required APIs..."
$REQUIRED_APIS = @(
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "containerregistry.googleapis.com",
    "speech.googleapis.com",
    "texttospeech.googleapis.com"
)

foreach ($api in $REQUIRED_APIS) {
    $enabled = gcloud services list --enabled --filter="name:$api" --format="value(name)" 2>&1
    if ($enabled -match $api) {
        Write-Success "API enabled: $api"
    } else {
        Write-Warning "API not enabled: $api"
        Write-Info "Enabling $api..."
        gcloud services enable $api
        Write-Success "Enabled $api"
    }
}

# =============================================================================
# Environment Variables Setup
# =============================================================================

Write-Header "Environment Variables Configuration"

Write-Warning "You need to provide the following environment variables."
Write-Host ""

# Load existing .env if it exists
$envVars = @{}
if (Test-Path ".env") {
    Write-Info "Loading existing .env file..."
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.+)$") {
            $envVars[$matches[1]] = $matches[2]
        }
    }
}

# Function to prompt for environment variable
function Get-EnvVar {
    param(
        [string]$VarName,
        [string]$Description,
        [bool]$IsSecret = $false,
        [string]$CurrentValue = ""
    )

    Write-Host "$VarName ($Description)" -ForegroundColor Yellow

    if ($CurrentValue) {
        $preview = $CurrentValue.Substring(0, [Math]::Min(20, $CurrentValue.Length)) + "..."
        Write-Host "Current value: $preview" -ForegroundColor Cyan
        $keep = Read-Host "Keep current value? (Y/n)"
        if ($keep -ne "n") {
            return $CurrentValue
        }
    }

    if ($IsSecret) {
        $secure = Read-Host "Enter value" -AsSecureString
        $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        return [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    } else {
        return Read-Host "Enter value"
    }
}

# Collect environment variables
Write-Host ""
Write-Info "Please provide the following configuration values:"
Write-Host ""

$MONGODB_URI = Get-EnvVar "MONGODB_URI" "MongoDB Atlas connection string" $true $envVars["MONGODB_URI"]
$GEMINI_API_KEY = Get-EnvVar "GEMINI_API_KEY" "Google Gemini API key" $true $envVars["GEMINI_API_KEY"]
$WABA_API_URL = Get-EnvVar "WABA_API_URL" "WhatsApp Business API URL" $false $(if ($envVars["WABA_API_URL"]) { $envVars["WABA_API_URL"] } else { "https://graph.facebook.com/v18.0" })
$WABA_PHONE_NUMBER_ID = Get-EnvVar "WABA_PHONE_NUMBER_ID" "WhatsApp Phone Number ID" $false $envVars["WABA_PHONE_NUMBER_ID"]
$WABA_ACCESS_TOKEN = Get-EnvVar "WABA_ACCESS_TOKEN" "WhatsApp Access Token" $true $envVars["WABA_ACCESS_TOKEN"]
$WABA_VERIFY_TOKEN = Get-EnvVar "WABA_VERIFY_TOKEN" "WhatsApp Verify Token" $true $envVars["WABA_VERIFY_TOKEN"]
$GCP_PROJECT_ID = Get-EnvVar "GCP_PROJECT_ID" "GCP Project ID for STT/TTS" $false $(if ($envVars["GCP_PROJECT_ID"]) { $envVars["GCP_PROJECT_ID"] } else { $PROJECT_ID })

# Redis configuration
Write-Host ""
Write-Info "Redis Configuration (use managed Redis or Cloud Memorystore)"
$REDIS_HOST = Get-EnvVar "REDIS_HOST" "Redis host address" $false $envVars["REDIS_HOST"]
$REDIS_PORT = Get-EnvVar "REDIS_PORT" "Redis port" $false $(if ($envVars["REDIS_PORT"]) { $envVars["REDIS_PORT"] } else { "6379" })
$REDIS_PASSWORD = Get-EnvVar "REDIS_PASSWORD" "Redis password (leave empty if none)" $true $envVars["REDIS_PASSWORD"]

# =============================================================================
# Build and Deploy
# =============================================================================

Write-Header "Building and Deploying to Cloud Run"

# Build the container
Write-Info "Building Docker container..."
gcloud builds submit --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" --timeout=20m .

Write-Success "Container built successfully"

# Deploy to Cloud Run
Write-Info "Deploying to Cloud Run..."

# Prepare environment variables
$ENV_VARS = @(
    "ENV=production",
    "DEBUG=false",
    "LOG_LEVEL=INFO",
    "APP_NAME=WhatsApp Voice AI",
    "API_VERSION=v1",
    "HOST=0.0.0.0",
    "PORT=8080",
    "MONGODB_URI=$MONGODB_URI",
    "MONGODB_DB_NAME=healthcare_ai",
    "MONGODB_COLLECTION=doctors",
    "MONGODB_VECTOR_COLLECTION=treatment_protocols",
    "REDIS_HOST=$REDIS_HOST",
    "REDIS_PORT=$REDIS_PORT",
    "REDIS_DB=0",
    "REDIS_PASSWORD=$REDIS_PASSWORD",
    "CONTEXT_TTL=1800",
    "GCP_PROJECT_ID=$GCP_PROJECT_ID",
    "GCP_STT_LANGUAGE=ur-PK",
    "GCP_TTS_LANGUAGE=ur-PK",
    "GCP_TTS_VOICE_NAME=ur-PK-Standard-A",
    "GEMINI_API_KEY=$GEMINI_API_KEY",
    "GEMINI_MODEL=gemini-1.5-flash",
    "WABA_API_URL=$WABA_API_URL",
    "WABA_PHONE_NUMBER_ID=$WABA_PHONE_NUMBER_ID",
    "WABA_ACCESS_TOKEN=$WABA_ACCESS_TOKEN",
    "WABA_VERIFY_TOKEN=$WABA_VERIFY_TOKEN",
    "MAX_MESSAGES_PER_USER=10",
    "RATE_LIMIT_WINDOW=60"
) -join ","

gcloud run deploy $SERVICE_NAME `
    --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" `
    --region $REGION `
    --platform managed `
    --allow-unauthenticated `
    --memory $MEMORY `
    --cpu $CPU `
    --timeout $TIMEOUT `
    --max-instances $MAX_INSTANCES `
    --min-instances $MIN_INSTANCES `
    --set-env-vars $ENV_VARS

Write-Success "Deployment completed!"

# =============================================================================
# Post-deployment Information
# =============================================================================

Write-Header "Deployment Information"

$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)"

Write-Host ""
Write-Success "Service deployed successfully!"
Write-Host ""
Write-Host "Service URL: " -NoNewline; Write-Host $SERVICE_URL -ForegroundColor Green
Write-Host "Webhook URL: " -NoNewline; Write-Host "$SERVICE_URL/api/v1/webhook" -ForegroundColor Green
Write-Host "Health Check: " -NoNewline; Write-Host "$SERVICE_URL/api/v1/health" -ForegroundColor Green
Write-Host ""

Write-Header "Next Steps"
Write-Host ""
Write-Host "1. Configure WhatsApp Webhook:"
Write-Host "   - Go to Meta Developer Portal"
Write-Host "   - Set webhook URL: $SERVICE_URL/api/v1/webhook"
Write-Host "   - Set verify token: $WABA_VERIFY_TOKEN"
Write-Host ""
Write-Host "2. Test the deployment:"
Write-Host "   curl $SERVICE_URL/api/v1/health"
Write-Host ""
Write-Host "3. Monitor logs:"
Write-Host "   gcloud run services logs tail $SERVICE_NAME --region $REGION"
Write-Host ""
Write-Host "4. View service details:"
Write-Host "   gcloud run services describe $SERVICE_NAME --region $REGION"
Write-Host ""

Write-Success "Deployment script completed successfully!"
