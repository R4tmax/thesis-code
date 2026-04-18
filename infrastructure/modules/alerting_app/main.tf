# 1. IDENTITY & IAM BINDINGS

resource "google_service_account" "alert_sa" {
  project      = var.project_id
  account_id   = "sa-alerting-${var.environment}"
  display_name = "BehavioBOT Alerting Function SA (${var.environment})"
}

# Project-Level Bindings: BigQuery
resource "google_project_iam_member" "bq_data_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.alert_sa.email}"
}

resource "google_project_iam_member" "bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.alert_sa.email}"
}

# Resource-Level Bindings: Secret Manager
data "google_secret_manager_secret" "mailgun_api" {
  project   = var.project_id
  secret_id = "mailgun-api-${var.environment}"
}

resource "google_secret_manager_secret_iam_member" "api_accessor" {
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.mailgun_api.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.alert_sa.email}"
}

data "google_secret_manager_secret" "mailgun_domain" {
  project   = var.project_id
  secret_id = "mailgun-domain-${var.environment}"
}

resource "google_secret_manager_secret_iam_member" "domain_accessor" {
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.mailgun_domain.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.alert_sa.email}"
}

# 2. STORAGE
resource "google_storage_bucket" "config_bucket" {
  project                     = var.project_id
  name                        = "${var.project_id}-alerting-config-${var.environment}"
  location                    = var.region
  uniform_bucket_level_access = true

  labels = {
    component = "custom-alerting"
  }
}

resource "google_storage_bucket" "source_bucket" {
  project                     = var.project_id
  name                        = "${var.project_id}-alerting-source-${var.environment}"
  location                    = var.region
  uniform_bucket_level_access = true

  labels = {
    component = "custom-alerting"
  }
}

resource "google_storage_bucket_object" "function_zip" {
  name   = "bootstrap-source.zip"
  bucket = google_storage_bucket.source_bucket.name
  # hardcoded bootstrap file
  source = "${path.module}/dummy.zip"
}

resource "google_storage_bucket_iam_member" "config_reader" {
  bucket = google_storage_bucket.config_bucket.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.alert_sa.email}"
}

# 3. COMPUTE: CLOUD RUN FUNCTION

resource "google_cloudfunctions2_function" "alerting_function" {
  project  = var.project_id
  name     = "behavio-alerting-${var.environment}"
  location = var.region

  labels = {
    component = "custom-alerting"
  }

  build_config {
    runtime     = "python312"
    entry_point = "read_and_alert"
    source {
      storage_source {
        bucket = google_storage_bucket.source_bucket.name
        object = google_storage_bucket_object.function_zip.name
      }
    }
  }

  service_config {
    min_instance_count    = 0
    max_instance_count    = 1
    available_memory      = "256M"
    timeout_seconds       = 60
    service_account_email = google_service_account.alert_sa.email

    environment_variables = {
      PROJECT_ID      = var.project_id
      GCS_BUCKET_NAME = google_storage_bucket.config_bucket.name
      GCS_BLOB_NAME   = "alert_definitions.yaml"
    }
  }

  lifecycle {
    ignore_changes = [
      build_config[0].source,
      build_config[0].environment_variables
    ]
  }
}

resource "google_cloud_run_v2_service_iam_member" "invoker" {
  project  = google_cloudfunctions2_function.alerting_function.project
  location = google_cloudfunctions2_function.alerting_function.location
  name     = google_cloudfunctions2_function.alerting_function.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.alert_sa.email}"
}

# 4. ORCHESTRATION: CLOUD SCHEDULER

resource "google_cloud_scheduler_job" "trigger_job" {
  project  = var.project_id
  region   = var.region
  name     = "alerting-trigger-${var.environment}"
  schedule = "5 * * * *"
  #  schedule  = "5 5 * * 6"
  time_zone = "Europe/Prague"

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.alerting_function.service_config[0].uri
    body        = base64encode(jsonencode({ "report_type" : "trigger" }))
    headers     = { "Content-Type" = "application/json" }

    oidc_token {
      service_account_email = google_service_account.alert_sa.email
    }
  }
}

resource "google_cloud_scheduler_job" "report_job" {
  project  = var.project_id
  region   = var.region
  name     = "alerting-report-${var.environment}"
  schedule = "0 * * * *"
  #  schedule  = "0 5 * * 6"
  time_zone = "Europe/Prague"

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.alerting_function.service_config[0].uri
    body        = base64encode(jsonencode({ "report_type" : "report" }))
    headers     = { "Content-Type" = "application/json" }

    oidc_token {
      service_account_email = google_service_account.alert_sa.email
    }
  }
}