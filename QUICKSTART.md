# Quick Start - Deploy to Google Cloud Run

Get your WhatsApp AI Assistant running on Google Cloud in **10 minutes**.

## 🚀 Option 1: Windows (PowerShell)

```powershell
# 1. Install Google Cloud SDK
# Download from: https://cloud.google.com/sdk/docs/install

# 2. Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 3. Deploy
.\deploy.ps1
```

## 🚀 Option 2: Mac/Linux (Bash)

```bash
# 1. Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# 2. Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 3. Make script executable and deploy
chmod +x deploy.sh
./deploy.sh
```

## 🚀 Option 3: Manual Deployment

### Prerequisites

```bash
# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable speech.googleapis.com
gcloud services enable texttospeech.googleapis.com
```

### Set Environment Variables

Create a `.env` file:

```bash
# MongoDB
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/

# Redis
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# WhatsApp Business API
WABA_API_URL=https://graph.facebook.com/v18.0
WABA_PHONE_NUMBER_ID=your-phone-number-id
WABA_ACCESS_TOKEN=your-access-token
WABA_VERIFY_TOKEN=your-verify-token

# Google Cloud
GCP_PROJECT_ID=your-project-id
```

### Build and Deploy

```bash
# Get your project ID
export PROJECT_ID=$(gcloud config get-value project)

# Build container
gcloud builds submit --tag gcr.io/$PROJECT_ID/whatsapp-ai-assistant

# Deploy to Cloud Run
gcloud run deploy whatsapp-ai-assistant \
    --image gcr.io/$PROJECT_ID/whatsapp-ai-assistant \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --set-env-vars-file .env
```

## ✅ Verify Deployment

```bash
# Get service URL
gcloud run services describe whatsapp-ai-assistant \
    --region us-central1 \
    --format "value(status.url)"

# Test health check
curl https://your-service-url.run.app/api/v1/health
```

## 🔧 Configure WhatsApp Webhook

1. Go to [Meta Developer Portal](https://developers.facebook.com/)
2. Select your WhatsApp Business App
3. Go to **WhatsApp > Configuration**
4. Set webhook URL: `https://your-service-url.run.app/api/v1/webhook`
5. Set verify token: (your `WABA_VERIFY_TOKEN` value)
6. Subscribe to fields: `messages`

## 🎉 Test Your Bot

Send a message to your WhatsApp Business number:
- "Hello" → Should receive language selection menu
- "1" → Select Urdu
- "2" → Select English

## 📊 Monitor Logs

```bash
# View real-time logs
gcloud run services logs tail whatsapp-ai-assistant --region us-central1

# View recent logs
gcloud run services logs read whatsapp-ai-assistant --region us-central1 --limit 50
```

## 🔄 Update After Code Changes

```bash
# Quick redeploy (keeps existing env vars)
chmod +x deploy-quick.sh
./deploy-quick.sh
```

## 📚 Need More Help?

- **Full Guide**: See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Troubleshooting**: Check logs and verify environment variables
- **Cloud Run Docs**: https://cloud.google.com/run/docs

## 💰 Cost Estimate

- **Cloud Run**: ~$5-10/month (100K messages)
- **Free Tier**: First 2 million requests/month FREE
- **MongoDB Atlas**: $0 (M0 Free Tier)
- **Redis**: Use Upstash free tier or Memorystore ($40/month)

---

**Your WhatsApp AI Assistant will be live in minutes! 🚀**
