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
