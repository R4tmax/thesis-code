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