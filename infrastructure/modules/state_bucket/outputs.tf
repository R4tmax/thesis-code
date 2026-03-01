output "bucket_name" {
  description = "The name of the created state bucket"
  value       = google_storage_bucket.remote_state_bucket.name
}