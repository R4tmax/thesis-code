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