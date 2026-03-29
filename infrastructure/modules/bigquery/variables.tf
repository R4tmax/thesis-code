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
  default     = "EUROPE-WEST3"
}

variable "delete_contents_on_destroy" {
  description = "Teardown policy, if true, dataset is non-persistent, defaults to False (prod)"
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Teardown protection, defaults to True (prod)"
  type        = bool
  default     = true
}