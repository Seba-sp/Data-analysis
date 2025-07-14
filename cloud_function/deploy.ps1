# Google Cloud Functions Deployment Script (PowerShell)
# This script deploys the course analysis pipeline to Google Cloud Functions

param(
    [string]$FunctionName = "course-analysis-pipeline",
    [string]$Region = "us-central1",
    [string]$Runtime = "python39",
    [string]$Memory = "2GB",
    [string]$Timeout = "540s"
)

# Configuration
$EntryPoint = "course_analysis_pipeline"
$TriggerType = "http"

Write-Host "🚀 Deploying Google Cloud Function: $FunctionName" -ForegroundColor Green

# Check if gcloud is installed
try {
    $gcloudVersion = gcloud version --format="value(basic.version)" 2>$null
    if (-not $gcloudVersion) {
        Write-Host "❌ Google Cloud SDK is not installed. Please install it first." -ForegroundColor Red
        Write-Host "Visit: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "✅ Google Cloud SDK version: $gcloudVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Google Cloud SDK is not installed. Please install it first." -ForegroundColor Red
    Write-Host "Visit: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    exit 1
}

# Check if user is authenticated
try {
    $authAccount = gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>$null
    if (-not $authAccount) {
        Write-Host "⚠️  You are not authenticated with Google Cloud." -ForegroundColor Yellow
        Write-Host "Please run: gcloud auth login" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "✅ Authenticated as: $authAccount" -ForegroundColor Green
} catch {
    Write-Host "⚠️  You are not authenticated with Google Cloud." -ForegroundColor Yellow
    Write-Host "Please run: gcloud auth login" -ForegroundColor Yellow
    exit 1
}

# Check if project is set
try {
    $ProjectId = gcloud config get-value project 2>$null
    if (-not $ProjectId) {
        Write-Host "❌ No Google Cloud project is set." -ForegroundColor Red
        Write-Host "Please set your project: gcloud config set project YOUR_PROJECT_ID" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "✅ Using project: $ProjectId" -ForegroundColor Green
} catch {
    Write-Host "❌ No Google Cloud project is set." -ForegroundColor Red
    Write-Host "Please set your project: gcloud config set project YOUR_PROJECT_ID" -ForegroundColor Yellow
    exit 1
}

# Check if env.yaml exists
if (-not (Test-Path "env.yaml")) {
    Write-Host "❌ env.yaml file not found. Please create it with your environment variables." -ForegroundColor Red
    Write-Host "Copy env.yaml.example to env.yaml and fill in your values." -ForegroundColor Yellow
    exit 1
}

# Enable required APIs
Write-Host "📋 Enabling required Google Cloud APIs..." -ForegroundColor Yellow
try {
    gcloud services enable cloudfunctions.googleapis.com
    gcloud services enable cloudbuild.googleapis.com
    gcloud services enable storage.googleapis.com
    gcloud services enable drive.googleapis.com
    Write-Host "✅ APIs enabled successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to enable APIs: $_" -ForegroundColor Red
    exit 1
}

# Deploy the function
Write-Host "📦 Deploying function..." -ForegroundColor Yellow
try {
    $deployCommand = @(
        "gcloud", "functions", "deploy", $FunctionName,
        "--runtime=$Runtime",
        "--region=$Region",
        "--source=.",
        "--entry-point=$EntryPoint",
        "--trigger-$TriggerType",
        "--memory=$Memory",
        "--timeout=$Timeout",
        "--env-vars-file=env.yaml",
        "--allow-unauthenticated"
    )
    
    & $deployCommand[0] $deployCommand[1..($deployCommand.Length-1)]
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Function deployment failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Deployment error: $_" -ForegroundColor Red
    exit 1
}

# Get the function URL
try {
    $FunctionUrl = gcloud functions describe $FunctionName --region=$Region --format="value(httpsTrigger.url)" 2>$null
    if (-not $FunctionUrl) {
        Write-Host "⚠️  Could not retrieve function URL" -ForegroundColor Yellow
    } else {
        Write-Host "✅ Function deployed successfully!" -ForegroundColor Green
        Write-Host "🌐 Function URL: $FunctionUrl" -ForegroundColor Green
        Write-Host "📊 Function name: $FunctionName" -ForegroundColor Green
        Write-Host "📍 Region: $Region" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Could not retrieve function URL: $_" -ForegroundColor Yellow
}

# Test the function
Write-Host "🧪 Testing the function..." -ForegroundColor Yellow
try {
    if ($FunctionUrl) {
        $testBody = '{"test": "true"}'
        $headers = @{
            "Content-Type" = "application/json"
        }
        
        $response = Invoke-RestMethod -Uri $FunctionUrl -Method POST -Body $testBody -Headers $headers -TimeoutSec 30
        Write-Host "✅ Function test successful" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Function test failed: $_" -ForegroundColor Yellow
}

Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Yellow
Write-Host "1. Set up a Cloud Scheduler job to trigger the function daily"
Write-Host "2. Monitor the function logs: gcloud functions logs read $FunctionName --region=$Region"
Write-Host "3. View function details: gcloud functions describe $FunctionName --region=$Region" 