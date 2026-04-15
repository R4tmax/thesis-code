provider "google" {
  project        = var.dev_proj_id
  region         = "europe-west3"
  default_labels = var.default_labels
}

module "state_bucket" {
  source = "../../modules/state_bucket"

  project_id  = var.dev_proj_id
  bucket_name = "${var.dev_proj_id}_state_bucket"
  location    = "EUROPE-WEST3"
}

locals {
  required_apis = [
    "aiplatform.googleapis.com",       # Vertex AI (Gemini models)
    "dns.googleapis.com",              # Cloud DNS (For Mailgun delegation)
    "storage.googleapis.com",          # Cloud Storage (State, Config, and Source buckets)
    "bigquery.googleapis.com",         # BigQuery (Datasets, Tables, Views)
    "artifactregistry.googleapis.com", # Artifact Registry (Docker images)
    "run.googleapis.com",              # Cloud Run (NLP App + underlying Alerting compute)
    "cloudfunctions.googleapis.com",   # Cloud Functions (Alerting App generation)
    "cloudbuild.googleapis.com",       # Required by Cloud Functions to build your Python zip
    "cloudscheduler.googleapis.com",   # Cloud Scheduler (Triggering the alerts)
    "secretmanager.googleapis.com",    # Secret Manager (OAuth, Mailgun keys)
    "iam.googleapis.com",              # IAM API (Creating Service Accounts and bindings)
    "iamcredentials.googleapis.com",   # Required for Cloud Scheduler to generate OIDC tokens!
  ]
}

resource "google_project_service" "enabled_apis" {
  for_each = toset(local.required_apis)
  project  = var.dev_proj_id
  service  = each.key

  disable_on_destroy = false
}

module "bigquery_database" {
  depends_on = [google_project_service.enabled_apis]
  source     = "../../modules/bigquery"

  project_id  = var.dev_proj_id
  environment = "dev"
  location    = "EUROPE-WEST3"

  delete_contents_on_destroy = true
  deletion_protection        = false
}

resource "google_artifact_registry_repository" "app_registry" {
  depends_on    = [google_project_service.enabled_apis]
  provider      = google
  project       = var.dev_proj_id
  location      = "europe-west3"
  repository_id = "behavio-repo-dev"
  description   = "Docker repository for the Behavio MVP"
  format        = "DOCKER"
  labels = {
    component = "behavio-bot"
  }
}

module "nlp_app" {
  depends_on = [google_project_service.enabled_apis]
  source     = "../../modules/behavio_bot"


  project_id  = var.dev_proj_id
  environment = "dev"
  location    = "europe-west3"
  app_name    = "behavio-bot"

  dataset_id          = module.bigquery_database.dataset_id
  oauth_client_id     = var.oauth_client_id
  oauth_redirect_uri  = "https://behavio-bot-dev-1083167021866.europe-west3.run.app"
  whitelisted_emails  = "kadlec.m.90@gmail.com,kadm09@vse.cz"
  whitelisted_domains = "behavio.cz,behaviolabs.cz"
}

module "dev_mailgun_dns" {
  depends_on = [google_project_service.enabled_apis]
  source     = "../../modules/mailgun_dns"

  project_id  = "thesis-kadm09-dev"
  zone_name   = "martinkadlec-dev-zone"
  domain_name = "dev.martinkadlec.dev." # note the trailing dot, change the URL between ENVs
  environment = "dev"
  description = "DNS zone for usage for Mailgun API client"
}


module "alerting_app" {
  depends_on = [google_project_service.enabled_apis]
  source     = "../../modules/alerting_app"

  project_id  = "thesis-kadm09-dev"
  environment = "dev"
  region      = "europe-west3"
  source_dir  = "${path.module}/../../../src/automatedAlerting"
}