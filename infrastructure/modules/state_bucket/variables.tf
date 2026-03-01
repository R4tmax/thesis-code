
variable "project_id" {
  description = "The GCP project ID where the bucket will live"
  type        = string
}

variable "bucket_name" {
  description = "A globally unique name for the bucket"
  type        = string
}

variable "location" {
  # see https://docs.cloud.google.com/storage/docs/locations
  description = "The GCP location"
  type        = string
  default     = "EUROPE-WEST3"
}