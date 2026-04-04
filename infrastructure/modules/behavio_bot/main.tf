# 1. Service Account for the App
resource "google_service_account" "app_sa" {
  account_id   = "${var.app_name}-sa-${var.environment}"
  display_name = "SA for ${var.app_name} in ${var.environment}"
  project      = var.project_id
}

# 2. IAM Roles for the App SA
resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.app_sa.email}"
}

resource "google_project_iam_member" "bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.app_sa.email}"
}

resource "google_bigquery_dataset_iam_member" "bq_data_viewer" {
  project    = var.project_id
  dataset_id = var.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.app_sa.email}"
}

# 3. Secret Manager (Read-Only Data Fetch)
data "google_secret_manager_secret" "oauth_client_secret" {
  secret_id = "${var.app_name}-oauth-secret-${var.environment}"
  project   = var.project_id
}

# Grant the App SA permission to read this specific secret
resource "google_secret_manager_secret_iam_member" "secret_accessor" {
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.oauth_client_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_sa.email}"
}

# 4. The Cloud Run Service (The Empty Shell)
resource "google_cloud_run_v2_service" "app_service" {
  name     = "${var.app_name}-${var.environment}"
  location = var.location
  project  = var.project_id

  template {
    service_account = google_service_account.app_sa.email

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_VERTEX_LOCATION"
        value = var.location
      }
      env {
        name  = "GOOGLE_OAUTH_CLIENT_ID"
        value = var.oauth_client_id
      }
      env {
        name = "GOOGLE_OAUTH_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            # References the data block we defined above
            secret  = data.google_secret_manager_secret.oauth_client_secret.secret_id
            version = "latest"
          }
        }
      }
      ports {
        container_port = 8501
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version
    ]
  }
}

# Make it public
resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = google_cloud_run_v2_service.app_service.project
  location = google_cloud_run_v2_service.app_service.location
  name     = google_cloud_run_v2_service.app_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}