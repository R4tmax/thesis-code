variable "project_id" {
  description = "The GCP Project ID where the zone will be created"
  type        = string
}

variable "environment" {
  type = string
}

variable "zone_name" {
  description = "The internal GCP name for the DNS zone (e.g., martinkadlec-dev-zone)"
  type        = string
}

variable "domain_name" {
  description = "The actual domain name. Must end with a trailing period (e.g., dev.martinkadlec.dev.)"
  type        = string
}

variable "description" {
  description = "Description for the DNS zone"
  type        = string
  default     = "Managed DNS zone for Mailgun delegation"
}
