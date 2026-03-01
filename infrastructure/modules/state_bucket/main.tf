resource "google_storage_bucket" "remote_state_bucket" {
  name                        = var.bucket_name
  project                     = var.project_id
  location                    = var.location
  force_destroy               = false
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }
}