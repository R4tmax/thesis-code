variable "dev_proj_id" {
  type        = string
  default     = "thesis-kadm09-dev"
  description = "UUID of the project corresponding to the target provision"
}

variable "oauth_client_id" {
  description = "The Google OAuth Client ID passed down to the NLP app module"
  type        = string
  sensitive   = true # Keeps it hidden in CLI output!
}

#variable "dev-proj_designation" {
#  type        = string
#  default     = "kadm09-thesis"
#  description = "String representation to use when dealing /w global namespacing issues in GCP"
#}

#variable "dev_naming_prefix" {
#  type        = string
#  default     = "dev"
#  description = "String to prepend to all managed resources within ENV"
#}
