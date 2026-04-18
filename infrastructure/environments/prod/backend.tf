terraform {
  backend "gcs" {
    bucket = "thesis-kadm09-prod_state_bucket"
    prefix = "terraform/state"
  }
}
