#!/usr/bin/env bash
set -euo pipefail

echo "==> Deploying Unified torii-api to Cloud Run..."
gcloud run deploy torii-api \
  --image=us-central1-docker.pkg.dev/tori-507709/torii/api:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8000 \
  --cpu=1 \
  --memory=1Gi \
  --min-instances=0 \
  --max-instances=10 \
  --set-env-vars="^##^TORII_DATABASE_URL=postgresql://postgres.fffdozvnragwhdqypjzj:twoQtkPRtgEXSWnc@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require##TORII_JWT_SECRET_KEY=637a7c2e6a4f209d79b6c8360fb0ff6b468f371908480584d6838ca8969a6f00##TORII_APP_BASE_URL=https://visa.noruvalabs.com##TORII_MIGRATE_ON_STARTUP=false##TORII_SEED_ON_STARTUP=false##TORII_REQUIRE_EMAIL_VERIFICATION=true##TORII_SMTP_HOST=smtp.gmail.com##TORII_SMTP_PORT=587##TORII_SMTP_USER=noruvalabs@gmail.com##TORII_SMTP_PASSWORD=hbrzqjxsfkwwvqkm##TORII_SMTP_FROM_EMAIL=noruvalabs@gmail.com##TORII_SMTP_FROM_NAME=Torii##TORII_SMTP_TLS=true##TORII_AI_GROQ_API_KEY=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##TORII_AI_GROQ_MODEL=qwen/qwen3.8-27b##TORII_AI_GROQ_EXTRACT_MODEL=openai/gpt-oss-120b##TORII_AI_TAVILY_API_KEY=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##TORII_AI_SERVICE_URL=http://localhost:8000" \
  --quiet

API_URL=$(gcloud run services describe torii-api --region=us-central1 --format='value(status.url)')
echo "==> torii-api URL: ${API_URL}"

echo "==> Deploying torii-web to Cloud Run..."
gcloud run deploy torii-web \
  --image=us-central1-docker.pkg.dev/tori-507709/torii/web:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=3000 \
  --cpu=1 \
  --memory=512Mi \
  --min-instances=0 \
  --max-instances=10 \
  --set-env-vars="API_PROXY_TARGET=${API_URL},AI_PROXY_TARGET=${API_URL},NEXT_PUBLIC_GOOGLE_CLIENT_ID=529415836006-250vb6qgkpjtabm2hmj3jb9uuqkso1en.apps.googleusercontent.com" \
  --quiet

WEB_URL=$(gcloud run services describe torii-web --region=us-central1 --format='value(status.url)')
echo "==> torii-web URL: ${WEB_URL}"

echo "========================================="
echo "Deployment Complete!"
echo "Backend API & AI: ${API_URL}"
echo "Web Frontend:     ${WEB_URL}"
echo "========================================="
