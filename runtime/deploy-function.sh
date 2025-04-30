gcloud functions deploy check_and_send_alert \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars SENDGRID_API_KEY=your_api_key
