provider "google" {
  project = var.dev_proj_id
  region  = "europe-west3"
}

module "state_bucket" {
  source = "../../modules/state_bucket"

  project_id  = var.dev_proj_id
  bucket_name = "${var.dev_proj_id}_state_bucket"
  location    = "EUROPE-WEST3"
}

module "bigquery_database" {
  source = "../../modules/bigquery"

  project_id  = var.dev_proj_id
  environment = "dev"
  location    = "EUROPE-WEST3"

  delete_contents_on_destroy = true
  deletion_protection        = false
}

# 1. Artifact Registry for the Dev Environment Docker Images
resource "google_artifact_registry_repository" "app_registry" {
  provider      = google
  project       = var.dev_proj_id
  location      = "europe-west3"
  repository_id = "behavio-repo-dev"
  description   = "Docker repository for the Behavio MVP"
  format        = "DOCKER"
}

# 2. The App Infrastructure
module "nlp_app" {
  source = "../../modules/behavio_bot"

  project_id  = var.dev_proj_id
  environment = "dev"
  location    = "europe-west3"
  app_name    = "behavio-bot"

  dataset_id      = module.bigquery_database.dataset_id
  oauth_client_id = var.oauth_client_id
}