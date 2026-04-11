variable "project_id" {
  type = string
}
variable "environment" {
  type = string
}
variable "location" {
  type    = string
  default = "europe-west3"
}

variable "app_name" {
  type    = string
  default = "behavio-bot"
}

variable "dataset_id" {
  type = string
}
variable "oauth_client_id" {
  type = string
}

variable "oauth_redirect_uri" {
  description = "Google Oauth Client redirect URI, requires either custom domain or bootstrap"
  type        = string
}