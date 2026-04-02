# 1. Create the App Service Account
resource "google_service_account" "app_sa" {
  account_id   = "${var.app_name}-sa-${var.environment}"
  display_name = "SA for ${var.app_name} in ${var.environment}"
  project      = var.project_id
}

# 2. Grant IAM Roles to the Service Account
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

# Grant Read access to the specific dataset Terraform built earlier
resource "google_bigquery_dataset_iam_member" "bq_data_viewer" {
  project    = var.project_id
  dataset_id = var.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.app_sa.email}"
}

# 3. Create the Secret Manager Container (The Keys)
resource "google_secret_manager_secret" "oauth_client_secret" {
  secret_id = "${var.app_name}-oauth-secret-${var.environment}"
  project   = var.project_id
  replication {
    auto {}
  }
}

# Allow the Cloud Run SA to read the secret
resource "google_secret_manager_secret_iam_member" "secret_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.oauth_client_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_sa.email}"
}

# 4. Provision Cloud Run (The Compute)
resource "google_cloud_run_v2_service" "app_service" {
  name     = "${var.app_name}-${var.environment}"
  location = var.location
  project  = var.project_id

  template {
    service_account = google_service_account.app_sa.email

    containers {
      # Use a dummy image to bootstrap the service.
      # Your CD pipeline will overwrite this later.
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
        value = var.oauth_client_id # Passed as plain text (safe)
      }
      env {
        name = "GOOGLE_OAUTH_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.oauth_client_secret.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  # THIS IS THE MAGIC LINE: Terraform ignores future image updates
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version
    ]
  }
}

# Make it public (since your app handles OAuth)
resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = google_cloud_run_v2_service.app_service.project
  location = google_cloud_run_v2_service.app_service.location
  name     = google_cloud_run_v2_service.app_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}