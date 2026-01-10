# 🚀 DEPLOY NOW - Step-by-Step Execution Guide

Your application is ready to deploy! All critical bugs have been fixed. Follow these steps to deploy to Google Cloud Run.

---

## ✅ What Was Fixed

**Critical Bugs Resolved:**
- ✅ English voice messages transcription (was being transcribed as Urdu)
- ✅ Language detection logic (missing return statement)
- ✅ LLM response generation (missing return statement)
- ✅ STT variable name errors
- ✅ RAG service typos and missing awaits
- ✅ MongoDB URI validation
- ✅ All typos and variable scope issues

---

## 📋 Prerequisites Checklist

Before deploying, ensure you have:

- [ ] **Google Cloud Account** (with billing enabled)
- [ ] **MongoDB Atlas Account** (free M0 cluster is fine)
  - Get connection string: `mongodb+srv://username:password@cluster.mongodb.net/`
- [ ] **Redis Instance** (choose one):
  - Upstash Redis (free tier): https://upstash.com
  - Google Cloud Memorystore (paid)
  - Redis Labs (free tier): https://redis.com
- [ ] **WhatsApp Business Account**
  - Phone Number ID
  - Access Token
  - Verify Token (create your own, e.g., "my-secret-verify-token-123")
- [ ] **Google Gemini API Key**
  - Get from: https://makersuite.google.com/app/apikey
- [ ] **Google Cloud SDK Installed**
  - Windows: https://cloud.google.com/sdk/docs/install
  - Mac: `brew install google-cloud-sdk`
  - Linux: `curl https://sdk.cloud.google.com | bash`

---

## 🚀 DEPLOYMENT METHOD 1: Windows (PowerShell) - EASIEST

### Step 1: Open PowerShell as Administrator

```powershell
# Navigate to project directory
cd C:\Users\huzai\.claude-worktrees\Medical-AI-system\reverent-mclean
```

### Step 2: Authenticate with Google Cloud

```powershell
# Login to Google Cloud
gcloud auth login

# Set your project (replace with your actual project ID)
gcloud config set project YOUR_PROJECT_ID

# Example:
# gcloud config set project my-medical-ai-project
```

### Step 3: Run Deployment Script

```powershell
# Execute deployment script
.\deploy.ps1
```

The script will:
1. ✅ Check prerequisites
2. ✅ Enable required APIs
3. ✅ Prompt for environment variables
4. ✅ Build Docker container
5. ✅ Deploy to Cloud Run
6. ✅ Display your webhook URL

### Step 4: Copy the Webhook URL

After deployment completes, you'll see:
```
Service URL: https://whatsapp-ai-assistant-xxxxx-uc.a.run.app
Webhook URL: https://whatsapp-ai-assistant-xxxxx-uc.a.run.app/api/v1/webhook
```

**Save this webhook URL** - you'll need it for WhatsApp configuration.

---

## 🚀 DEPLOYMENT METHOD 2: Mac/Linux (Bash)

### Step 1: Open Terminal

```bash
# Navigate to project directory
cd ~/path/to/Medical-AI-system/reverent-mclean
```

### Step 2: Authenticate with Google Cloud

```bash
# Login to Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### Step 3: Make Script Executable and Deploy

```bash
# Make deployment script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

---

## 🚀 DEPLOYMENT METHOD 3: Manual (All Platforms)

### Step 1: Set Your Project

```bash
gcloud config set project YOUR_PROJECT_ID
export PROJECT_ID=$(gcloud config get-value project)
```

### Step 2: Enable APIs

```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable speech.googleapis.com
gcloud services enable texttospeech.googleapis.com
```

### Step 3: Build Container

```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/whatsapp-ai-assistant --timeout=20m
```

### Step 4: Deploy to Cloud Run

**Replace the values below with your actual credentials:**

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
HOST=0.0.0.0,\
PORT=8080,\
MONGODB_URI=mongodb+srv://YOUR_MONGO_USER:YOUR_MONGO_PASS@cluster.mongodb.net/,\
MONGODB_DB_NAME=healthcare_ai,\
MONGODB_COLLECTION=doctors,\
MONGODB_VECTOR_COLLECTION=treatment_protocols,\
REDIS_HOST=YOUR_REDIS_HOST,\
REDIS_PORT=6379,\
REDIS_PASSWORD=YOUR_REDIS_PASSWORD,\
REDIS_DB=0,\
CONTEXT_TTL=1800,\
GCP_PROJECT_ID=$PROJECT_ID,\
GCP_STT_LANGUAGE=ur-PK,\
GCP_TTS_LANGUAGE=ur-PK,\
GCP_TTS_VOICE_NAME=ur-PK-Standard-A,\
GEMINI_API_KEY=YOUR_GEMINI_KEY,\
GEMINI_MODEL=gemini-1.5-flash,\
WABA_API_URL=https://graph.facebook.com/v18.0,\
WABA_PHONE_NUMBER_ID=YOUR_PHONE_NUMBER_ID,\
WABA_ACCESS_TOKEN=YOUR_ACCESS_TOKEN,\
WABA_VERIFY_TOKEN=YOUR_VERIFY_TOKEN,\
MAX_MESSAGES_PER_USER=10,\
RATE_LIMIT_WINDOW=60"
```

---

## ✅ Step 5: Verify Deployment

### Get Service URL

```bash
gcloud run services describe whatsapp-ai-assistant \
    --region us-central1 \
    --format "value(status.url)"
```

### Test Health Endpoint

```bash
# Copy the URL from above command, then:
curl https://YOUR-SERVICE-URL.run.app/api/v1/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-10T12:00:00",
  "services": {
    "redis": "healthy",
    "mongodb": "healthy"
  },
  "version": "v1"
}
```

---

## 📱 Step 6: Configure WhatsApp Webhook

### 1. Go to Meta Developer Portal

Visit: https://developers.facebook.com/

### 2. Navigate to Your App

- Select your **WhatsApp Business App**
- Go to **WhatsApp > Configuration**

### 3. Configure Webhook

Click **Edit** button in Webhook section:

- **Callback URL**: `https://YOUR-SERVICE-URL.run.app/api/v1/webhook`
- **Verify Token**: (the value you set for `WABA_VERIFY_TOKEN`)

Click **Verify and Save**

### 4. Subscribe to Webhook Fields

Check these fields:
- ✅ **messages**
- ✅ **message_status** (optional)

Click **Save**

---

## 🎉 Step 7: Test Your Bot!

### Send Test Messages

Send these messages to your WhatsApp Business number:

**Test 1: Welcome Flow**
```
Send: "Hello"
Expected: Language selection menu (Urdu/English)
```

**Test 2: Language Selection**
```
Send: "2"
Expected: Mode selection (Voice/Text)
```

**Test 3: English Query**
```
Send: "Which doctors are available?"
Expected: English response with doctor information
```

**Test 4: Urdu Query**
```
Send: "کون سے ڈاکٹر دستیاب ہیں؟"
Expected: Urdu response with doctor information
```

---

## 📊 Step 8: Monitor Your Deployment

### View Real-time Logs

```bash
gcloud run services logs tail whatsapp-ai-assistant --region us-central1
```

### View Recent Logs

```bash
gcloud run services logs read whatsapp-ai-assistant \
    --region us-central1 \
    --limit 50
```

### View Errors Only

```bash
gcloud run services logs read whatsapp-ai-assistant \
    --region us-central1 \
    --filter "severity>=ERROR"
```

### View Service Details

```bash
gcloud run services describe whatsapp-ai-assistant --region us-central1
```

---

## 🔄 Update After Code Changes

### Quick Redeploy (Keeps Environment Variables)

**Windows:**
```powershell
.\deploy-quick.sh
```

**Mac/Linux:**
```bash
chmod +x deploy-quick.sh
./deploy-quick.sh
```

### Update Environment Variables Only

**Windows:**
```powershell
.\update-env-vars.sh
```

**Mac/Linux:**
```bash
chmod +x update-env-vars.sh
./update-env-vars.sh
```

---

## 🐛 Troubleshooting

### Issue: Build Fails

**Check build logs:**
```bash
gcloud builds list --limit 5
gcloud builds log <BUILD_ID>
```

### Issue: Service Returns 500 Error

**Check logs:**
```bash
gcloud run services logs tail whatsapp-ai-assistant --region us-central1
```

**Common causes:**
- Missing or invalid MongoDB URI
- Redis connection failed
- Invalid Gemini API key
- Missing environment variables

### Issue: Webhook Verification Fails

**Check:**
1. Verify token matches exactly (case-sensitive)
2. Service is publicly accessible
3. Webhook URL is correct

**Test webhook manually:**
```bash
curl "https://YOUR-SERVICE-URL.run.app/api/v1/webhook?hub.mode=subscribe&hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=test"
```

Should return: `test`

### Issue: Out of Memory

**Increase memory:**
```bash
gcloud run services update whatsapp-ai-assistant \
    --region us-central1 \
    --memory 2Gi
```

---

## 📞 Get Support

### Cloud Run Documentation
https://cloud.google.com/run/docs

### View Service in Console
https://console.cloud.google.com/run

### WhatsApp Business API Docs
https://developers.facebook.com/docs/whatsapp

### MongoDB Atlas Support
https://www.mongodb.com/cloud/atlas

---

## 💰 Cost Estimate

**Expected Monthly Costs (100K messages):**

| Service | Cost |
|---------|------|
| Cloud Run | $5-10 (2M requests FREE tier) |
| MongoDB Atlas M0 | $0 (Free tier) |
| Redis (Upstash) | $0 (Free tier) |
| Google STT/TTS | ~$10-20 |
| Gemini API | Free tier available |
| **Total** | **~$15-30/month** |

**Note:** First 2 million Cloud Run requests per month are FREE!

---

## ✅ Deployment Checklist

- [ ] Google Cloud SDK installed
- [ ] Authenticated with `gcloud auth login`
- [ ] Project set with `gcloud config set project`
- [ ] MongoDB Atlas connection string ready
- [ ] Redis host and credentials ready
- [ ] WhatsApp Business API credentials ready
- [ ] Gemini API key ready
- [ ] Deployment script executed successfully
- [ ] Service URL obtained
- [ ] Health check passed
- [ ] WhatsApp webhook configured
- [ ] Test messages sent and received
- [ ] Logs monitoring setup

---

## 🎊 Congratulations!

Your WhatsApp AI Assistant is now **LIVE** on Google Cloud Run!

**Next Steps:**
1. Monitor initial user interactions via logs
2. Test all language modes (Urdu, Roman Urdu, English)
3. Test symptom search functionality
4. Configure MongoDB with doctor data
5. Set up monitoring and alerts
6. Consider using Google Cloud Secret Manager for sensitive data

**Your service is production-ready with all critical bugs fixed! 🚀**

---

## 📚 Additional Resources

- **Full Deployment Guide**: See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Quick Start**: See [QUICKSTART.md](QUICKSTART.md)
- **Root Cause Analysis**: See previous analysis report
- **GitHub Repository**: https://github.com/huzaifa1134/Syalani-medical-ai

---

**Need help? Check the logs first!**
```bash
gcloud run services logs tail whatsapp-ai-assistant --region us-central1
```
