# Data Analysis Platform

Three specialized tools for educational data analysis, designed for Google Cloud Platform deployment.

## 🚀 Quick Start

### 1. **Course Analysis** (Batch Processing)
```bash
cd batch-processing
python batch_process.py
```

### 2. **Assessment Analysis** (Response Analysis)
```bash
cd assessment-responses
python analisis_responses.py --course <course> --all
```

### 3. **Real-time Processing** (Webhook Service)
```bash
cd webhook-service
python webhook_main.py
```

## 📚 Documentation

Each feature has its own detailed README:

- [Batch Processing](batch-processing/README.md) - Course analysis and report generation
- [Assessment Responses](assessment-responses/README.md) - Individual assessment analysis
- [Webhook Service](webhook-service/README.md) - Real-time processing and email delivery

## 🔧 Setup

1. **Environment Setup**
   ```bash
   python scripts/setup_environment.py
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   cp shared/env.template .env
   # Edit .env with your credentials
   ```

## 🏗️ Project Structure

```
data-analysis/
├── batch-processing/          # Course analysis (Cloud Run Job)
├── assessment-responses/      # Assessment analysis (Cloud Run Job)
├── webhook-service/          # Real-time processing (Cloud Run Service)
├── shared/                   # Shared utilities
├── scripts/                  # Setup and deployment scripts
└── data/                     # Data storage
```

## 💰 Cost Optimization

- **Batch Processing**: ~$1.62/month (daily execution)
- **Assessment Responses**: ~$0.36/month (weekly execution)
- **Webhook Service**: ~$0.12/month (1000 requests)
- **Storage**: ~$0.20/month (10GB)
- **Total**: ~$2.30/month

## 🚀 GCP Deployment

### Batch Processing (Cloud Run Job)
```bash
cd batch-processing
gcloud run jobs update batch-processing --image gcr.io/PROJECT/batch-processing:latest
```

### Webhook Service (Cloud Run Service)
```bash
cd webhook-service
gcloud run deploy webhook-service --image gcr.io/PROJECT/webhook-service:latest
```

### Assessment Responses (Cloud Run Job)
```bash
cd assessment-responses
gcloud run jobs update assessment-responses --image gcr.io/PROJECT/assessment-responses:latest
```

## 📊 Features

| Feature | Purpose | Deployment | Cost |
|---------|---------|------------|------|
| **Batch Processing** | Course analysis & reports | Cloud Run Job | ~$1.62/month |
| **Assessment Responses** | Assessment analysis | Cloud Run Job | ~$0.36/month |
| **Webhook Service** | Real-time processing | Cloud Run Service | ~$0.12/month |

## 🔍 Troubleshooting

- **Storage Issues**: Check `GCP_BUCKET_NAME` environment variable
- **Authentication**: Run `python scripts/setup_environment.py`
- **Deployment**: See individual feature READMEs for deployment guides
