gcloud scheduler jobs create http check-bq-alert \
  --schedule="0 8 * * *" \
  --uri=https://REGION-PROJECT.cloudfunctions.net/check_and_send_alert \
  --http-method=GET \
  --time-zone="UTC"
