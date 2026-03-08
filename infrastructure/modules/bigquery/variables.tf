variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "environment" {
  description = "The environment (dev or prod)"
  type        = string
}

variable "location" {
  description = "The GCP location for the dataset"
  type        = string
  default     = "EU"
}