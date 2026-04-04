output "service_url" {
  description = "The URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.app_service.uri
}

output "service_account_email" {
  description = "The email of the Service Account used by Cloud Run"
  value       = google_service_account.app_sa.email
}

output "secret_id" {
  description = "The ID of the Secret Manager secret for the OAuth Client Secret"
  value       = data.google_secret_manager_secret.oauth_client_secret.secret_id
}