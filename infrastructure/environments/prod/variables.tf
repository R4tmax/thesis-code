variable "proj_id" {
  type        = string
  description = "UUID of the project corresponding to the target provision"
}

variable "environment_label" {
  type        = string
  description = "label marking the env shorthand for usage in other variables and naming conventions"
}

variable "oauth_client_id" {
  description = "The Google OAuth Client ID passed down to the NLP app module"
  type        = string
  sensitive   = true
}

variable "default_labels" {
  description = "A standard set of labels to apply to all resources"
  type        = map(string)
  default = {
    managed_by  = "terraform"
    project     = "thesis"
    environment = "prod"
  }
}
