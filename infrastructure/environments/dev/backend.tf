terraform {
  backend "gcs" {
    bucket = "thesis-kadm09-dev_state_bucket"
    prefix = "terraform/state"
  }
}
