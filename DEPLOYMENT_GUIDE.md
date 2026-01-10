# Google Cloud Run Deployment Guide

Complete guide for deploying the WhatsApp AI Assistant to Google Cloud Run.

## Prerequisites

### 1. Install Google Cloud SDK

**Windows:**
```powershell
# Download and install from:
https://cloud.google.com/sdk/docs/install

# Or use chocolatey:
choco install gcloudsdk
```

**Mac/Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### 2. Authenticate with Google Cloud

```bash
# Login to your Google account
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable speech.googleapis.com
gcloud services enable texttospeech.googleapis.com
```

### 3. Required Services Setup

#### MongoDB Atlas
- Create MongoDB Atlas cluster (M0 Free Tier or higher)
- Get connection string: `mongodb+srv://username:password@cluster.mongodb.net/`
- Whitelist Google Cloud IP ranges or use `0.0.0.0/0` (all IPs)

#### Redis (Choose one)

**Option A: Google Cloud Memorystore** (Recommended for production)
```bash
gcloud redis instances create whatsapp-redis \
    --size=1 \
    --region=us-central1 \
    --redis-version=redis_7_0

# Get the host
gcloud redis instances describe whatsapp-redis --region=us-central1 --format="get(host)"
```

**Option B: Upstash Redis** (Free tier available)
- Create account at https://upstash.com
- Create Redis database
- Get connection details (host, port, password)

**Option C: Redis Labs Cloud** (Free tier available)
- Create account at https://redis.com/try-free/
- Create database
- Get connection details

#### WhatsApp Business API
- Create Meta Developer account
- Create WhatsApp Business App
- Get:
  - Phone Number ID
  - Access Token
  - Set Verify Token (create your own secure string)

#### Google Gemini API
- Get API key from: https://makersuite.google.com/app/apikey

---

## Deployment Methods

### Method 1: Automated Deployment (Recommended)

```bash
# Make script executable (Mac/Linux)
chmod +x deploy.sh

# Run deployment script
./deploy.sh
```

**For Windows:**
```powershell
# Use Git Bash or WSL, or run commands manually from deploy.sh
```

The script will:
1. ✓ Check prerequisites
2. ✓ Enable required APIs
3. ✓ Prompt for environment variables
4. ✓ Build Docker container
5. ✓ Deploy to Cloud Run
6. ✓ Display webhook URL

---

### Method 2: Manual Deployment

#### Step 1: Build the Container

```bash
# Set your project ID
export PROJECT_ID=your-project-id

# Build and submit to Container Registry
gcloud builds submit --tag gcr.io/$PROJECT_ID/whatsapp-ai-assistant
```

#### Step 2: Deploy to Cloud Run

```bash
gcloud run deploy whatsapp-ai-assistant \
    --image gcr.io/$PROJECT_ID/whatsapp-ai-assistant \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0 \
    --set-env-vars "\
ENV=production,\
DEBUG=false,\
LOG_LEVEL=INFO,\
APP_NAME=WhatsApp Voice AI,\
API_VERSION=v1,\
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/,\
MONGODB_DB_NAME=healthcare_ai,\
MONGODB_COLLECTION=doctors,\
MONGODB_VECTOR_COLLECTION=treatment_protocols,\
REDIS_HOST=your-redis-host,\
REDIS_PORT=6379,\
REDIS_PASSWORD=your-redis-password,\
REDIS_DB=0,\
CONTEXT_TTL=1800,\
GCP_PROJECT_ID=your-project-id,\
GCP_STT_LANGUAGE=ur-PK,\
GCP_TTS_LANGUAGE=ur-PK,\
GCP_TTS_VOICE_NAME=ur-PK-Standard-A,\
GEMINI_API_KEY=your-gemini-key,\
GEMINI_MODEL=gemini-1.5-flash,\
WABA_API_URL=https://graph.facebook.com/v18.0,\
WABA_PHONE_NUMBER_ID=your-phone-id,\
WABA_ACCESS_TOKEN=your-access-token,\
WABA_VERIFY_TOKEN=your-verify-token,\
MAX_MESSAGES_PER_USER=10,\
RATE_LIMIT_WINDOW=60"
```

---

### Method 3: Using Cloud Build (CI/CD)

```bash
# Deploy using cloudbuild.yaml
gcloud builds submit --config cloudbuild.yaml

# Note: You'll need to set environment variables separately
```

---

## Update Environment Variables

### Quick Update Script

```bash
chmod +x update-env-vars.sh
./update-env-vars.sh
```

### Manual Update

```bash
# Update single variable
gcloud run services update whatsapp-ai-assistant \
    --region us-central1 \
    --update-env-vars GEMINI_API_KEY=new-key

# Update multiple variables
gcloud run services update whatsapp-ai-assistant \
    --region us-central1 \
    --update-env-vars "VAR1=value1,VAR2=value2"

# Remove variable
gcloud run services update whatsapp-ai-assistant \
    --region us-central1 \
    --remove-env-vars VAR_NAME
```

---

## Quick Redeploy (After Code Changes)

```bash
chmod +x deploy-quick.sh
./deploy-quick.sh
```

---

## Configure WhatsApp Webhook

### Step 1: Get Your Service URL

```bash
gcloud run services describe whatsapp-ai-assistant \
    --region us-central1 \
    --format "value(status.url)"
```

Output example: `https://whatsapp-ai-assistant-abc123-uc.a.run.app`

### Step 2: Configure in Meta Developer Portal

1. Go to: https://developers.facebook.com
2. Select your WhatsApp Business App
3. Go to WhatsApp > Configuration
4. Click "Edit" on Webhook
5. Set:
   - **Callback URL**: `https://your-service-url.run.app/api/v1/webhook`
   - **Verify Token**: Your `WABA_VERIFY_TOKEN` value
6. Click "Verify and Save"
7. Subscribe to webhook fields:
   - ✓ messages
   - ✓ message_status (optional)

---

## Testing Deployment

### 1. Health Check

```bash
curl https://your-service-url.run.app/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-10T12:00:00",
  "services": {
    "redis": "healthy",
    "mongodb": "healthy",
    "gemini": "healthy"
  },
  "version": "v1"
}
```

### 2. Root Endpoint

```bash
curl https://your-service-url.run.app/
```

### 3. Send Test WhatsApp Message

Send a message to your WhatsApp Business number:
- Text: "Hello"
- Expected: Welcome message with language selection

---

## Monitoring

### View Logs

```bash
# Tail logs in real-time
gcloud run services logs tail whatsapp-ai-assistant --region us-central1

# View recent logs
gcloud run services logs read whatsapp-ai-assistant \
    --region us-central1 \
    --limit 50

# Filter logs
gcloud run services logs read whatsapp-ai-assistant \
    --region us-central1 \
    --filter "severity>=ERROR"
```

### View Metrics

```bash
# Open in Cloud Console
gcloud run services describe whatsapp-ai-assistant \
    --region us-central1
```

Or visit: https://console.cloud.google.com/run

---

## Troubleshooting

### Issue: Deployment Fails

**Check build logs:**
```bash
gcloud builds list --limit 5
gcloud builds log BUILD_ID
```

### Issue: Service Crashes on Startup

**Check logs:**
```bash
gcloud run services logs tail whatsapp-ai-assistant --region us-central1
```

Common causes:
- Missing environment variables (MongoDB URI, API keys)
- Invalid MongoDB URI format
- Redis connection failed
- Invalid Google Cloud credentials

### Issue: Webhook Verification Fails

**Check:**
1. Verify token matches exactly
2. Service is publicly accessible (`--allow-unauthenticated`)
3. Check logs for verification attempts

### Issue: Out of Memory

**Increase memory:**
```bash
gcloud run services update whatsapp-ai-assistant \
    --region us-central1 \
    --memory 2Gi
```

### Issue: Timeout Errors

**Increase timeout:**
```bash
gcloud run services update whatsapp-ai-assistant \
    --region us-central1 \
    --timeout 600
```

---

## Environment Variables Reference

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `ENV` | Environment | Yes | `production` |
| `DEBUG` | Debug mode | Yes | `false` |
| `LOG_LEVEL` | Logging level | Yes | `INFO` |
| `MONGODB_URI` | MongoDB connection | Yes | `mongodb+srv://...` |
| `REDIS_HOST` | Redis host | Yes | `10.0.0.3` |
| `REDIS_PORT` | Redis port | Yes | `6379` |
| `REDIS_PASSWORD` | Redis password | No | `your-password` |
| `GEMINI_API_KEY` | Gemini API key | Yes | `AIza...` |
| `WABA_PHONE_NUMBER_ID` | WhatsApp phone ID | Yes | `123456789` |
| `WABA_ACCESS_TOKEN` | WhatsApp token | Yes | `EAA...` |
| `WABA_VERIFY_TOKEN` | Webhook verify token | Yes | `your-secret-token` |
| `GCP_PROJECT_ID` | GCP project for STT/TTS | Yes | `my-project` |

---

## Scaling Configuration

### Auto-scaling Settings

```bash
# Minimum instances (0 = scale to zero)
--min-instances 0

# Maximum instances
--max-instances 10

# Concurrent requests per instance
--concurrency 80

# CPU allocation
--cpu-throttling  # or --no-cpu-throttling
```

### Cost Optimization

**Development/Testing:**
```bash
--min-instances 0
--max-instances 1
--memory 512Mi
```

**Production:**
```bash
--min-instances 1  # Always warm
--max-instances 10
--memory 1Gi
```

---

## Security Best Practices

### 1. Use Secret Manager (Recommended)

```bash
# Create secret
echo -n "your-secret-value" | gcloud secrets create mongodb-uri --data-file=-

# Grant access to Cloud Run
gcloud secrets add-iam-policy-binding mongodb-uri \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Deploy with secret
gcloud run deploy whatsapp-ai-assistant \
    --set-secrets "MONGODB_URI=mongodb-uri:latest"
```

### 2. Restrict Access

```bash
# Require authentication
gcloud run services update whatsapp-ai-assistant \
    --region us-central1 \
    --no-allow-unauthenticated

# Then use Cloud Endpoints or API Gateway for webhook
```

### 3. Enable VPC Connector (for private Redis/MongoDB)

```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create whatsapp-connector \
    --region us-central1 \
    --range 10.8.0.0/28

# Deploy with VPC
gcloud run deploy whatsapp-ai-assistant \
    --vpc-connector whatsapp-connector
```

---

## Continuous Deployment (GitHub Actions)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - id: auth
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Deploy to Cloud Run
        uses: google-github-actions/deploy-cloudrun@v1
        with:
          service: whatsapp-ai-assistant
          region: us-central1
          source: .
```

---

## Costs Estimate

**Cloud Run Pricing (us-central1):**
- First 2 million requests/month: FREE
- CPU: $0.00002400/vCPU-second
- Memory: $0.00000250/GiB-second
- Requests: $0.40/million requests

**Example Monthly Cost:**
- 100K messages/month
- ~2 seconds per request
- 1 vCPU, 1 GiB RAM
- Estimated: **$5-10/month**

**Additional Costs:**
- MongoDB Atlas: $0 (M0) - $57/month (M10)
- Redis Memorystore: $40/month (1GB)
- Google STT/TTS: $0.006/15 seconds
- Gemini API: Free tier available

---

## Support

For issues:
- Cloud Run: https://cloud.google.com/run/docs
- MongoDB Atlas: https://docs.atlas.mongodb.com/
- WhatsApp Business API: https://developers.facebook.com/docs/whatsapp

---

**Deployment completed! Your WhatsApp AI Assistant is now live on Google Cloud Run.**
