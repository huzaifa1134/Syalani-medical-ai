# 🏥 WhatsApp Voice AI - Healthcare Assistant

Production-ready WhatsApp voice assistant for healthcare using FastAPI, Gemini AI, and MongoDB Atlas.

## 🎯 Features

- ✅ Voice message processing (Urdu)
- ✅ Text message support
- ✅ Context-aware conversations (30-minute memory)
- ✅ RAG with MongoDB Atlas Vector Search
- ✅ Professional Urdu voice responses
- ✅ Doctor search and appointment scheduling
- ✅ Treatment information retrieval

## 🏗️ Architecture

```
User (WhatsApp) 
    ↓
WhatsApp Business API
    ↓
FastAPI Webhook
    ↓
[STT] → [Context] → [RAG] → [LLM] → [TTS]
    ↓
WhatsApp Response
```

## 📋 Prerequisites

- Python 3.11+
- MongoDB Atlas account (with Vector Search)
- Google Cloud account (STT/TTS enabled)
- Gemini API key
- WhatsApp Business API access
- Redis server

## 🚀 Installation

### 1. Clone Repository

```bash
git clone <your-repo>
cd whatsapp-voice-ai
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials.

### 5. Setup Google Cloud Credentials

1. Download your service account JSON key
2. Save it as `service-account-key.json` in project root
3. Update `GOOGLE_APPLICATION_CREDENTIALS` path in `.env`

### 6. Setup MongoDB Atlas Vector Search

Create a vector search index on your treatment collection:

```javascript
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "embedding": {
        "type": "knnVector",
        "dimensions": 768,
        "similarity": "cosine"
      }
    }
  }
}
```

## 📊 Database Structure

### Doctors Collection (JSON)

```json
{
  "name": "Dr. Ahmed Khan",
  "specialty": "Cardiology",
  "timings": [
    {
      "day": "Monday",
      "time": "9:00 AM - 1:00 PM"
    }
  ],
  "location": "Karachi Medical Center",
  "phone": "+92-XXX-XXXXXXX"
}
```

### Treatment Protocols Collection (Vector)

```json
{
  "title": "Heart Disease Treatment",
  "content": "Detailed treatment information...",
  "category": "Cardiology",
  "embedding": [0.123, 0.456, ...]
}
```

## 🏃 Running the Application

### Development Mode

```bash
python -m app.main
```

Or with uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🔗 Webhook Setup

### 1. Expose Your Local Server (Development)

Use ngrok:

```bash
ngrok http 8000
```

### 2. Configure WhatsApp Webhook

1. Go to Meta for Developers
2. Configure Webhook URL: `https://your-domain.com/api/v1/webhook`
3. Set Verify Token (same as `WABA_VERIFY_TOKEN` in `.env`)
4. Subscribe to `messages` events

## 📡 API Endpoints

### Webhook Endpoints

- `GET /api/v1/webhook` - Webhook verification
- `POST /api/v1/webhook` - Receive WhatsApp messages

### Health Check

- `GET /api/v1/health` - Service health status
- `GET /api/v1/health/ping` - Simple ping

### Root

- `GET /` - API information
- `GET /api` - Endpoints list

## 🧪 Testing

### Test Webhook Verification

```bash
curl "http://localhost:8000/api/v1/webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=test123"
```

### Test Health Check

```bash
curl http://localhost:8000/api/v1/health
```

## 📝 Logging

Logs are structured JSON (production) or colored console (development).

View logs:

```bash
# Development
python -m app.main

# Production
tail -f logs/app.log
```

## 🔧 Configuration

All configuration is in `.env`:

- `DEBUG=True` - Enable debug mode
- `LOG_LEVEL=INFO` - Set log level
- `CONTEXT_TTL=1800` - Context expiry (30 minutes)
- `MAX_MESSAGES_PER_USER=10` - Rate limiting

## 🐛 Troubleshooting

### Redis Connection Failed

```bash
# Start Redis
redis-server

# Test connection
redis-cli ping
```

### MongoDB Connection Failed

- Check MongoDB Atlas whitelist
- Verify connection string
- Check network access

### Google Cloud Errors

- Verify service account permissions
- Check API enablement (STT, TTS)
- Verify credentials path

### WhatsApp Webhook Not Receiving

- Check webhook URL is public
- Verify HTTPS (required by Meta)
- Check webhook verification token

## 📈 Monitoring

### Check Service Health

```bash
curl http://localhost:8000/api/v1/health
```

### Monitor Logs

```bash
tail -f logs/app.log | jq
```

## 🔐 Security

- Never commit `.env` or credentials
- Use HTTPS in production
- Implement rate limiting
- Validate webhook signatures
- Use environment-specific configs

## 📦 Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Cloud Platforms

- **Google Cloud Run**: Fully managed, auto-scaling
- **AWS Elastic Beanstalk**: Easy deployment
- **DigitalOcean App Platform**: Simple and affordable
- **Railway**: Fast deployment

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📄 License

MIT License

## 🆘 Support

For issues or questions:
- Create GitHub issue
- Check documentation
- Review logs

## 🎉 Next Steps

1. Set up all credentials
2. Test webhook locally
3. Deploy to production
4. Monitor and optimize
5. Add more features

---

**Made with ❤️ for Healthcare**