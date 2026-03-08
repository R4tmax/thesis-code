resource "google_service_account" "github_actions_sa" {
  account_id   = "github-actions-sa"
  display_name = "Service Account for GitHub Actions CI/CD"
}

resource "google_project_iam_member" "sa_default_role" {
  project = var.dev_proj_id
  role    = "roles/reader"
  member  = "serviceAccount:${google_service_account.github_actions_sa.email}"
}

resource "google_iam_workload_identity_pool" "github_pool" {
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions Pool"
  description               = "Identity pool for GitHub Actions deployments"
}

resource "google_iam_workload_identity_pool_provider" "github_provider" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  attribute_condition = "assertion.repository == 'R4tmax/thesis-code'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_actions_sa_binding" {
  service_account_id = google_service_account.github_actions_sa.name
  role               = "roles/iam.workloadIdentityUser"

  member = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool.name}/attribute.repository/R4tmax/thesis-code"
}


output "github_actions_provider_name" {
  value       = google_iam_workload_identity_pool_provider.github_provider.name
  description = "The Workload Identity Provider name to put in your GitHub Actions YAML"
}

output "github_actions_sa_email" {
  value       = google_service_account.github_actions_sa.email
  description = "The Service Account email to put in your GitHub Actions YAML"
}