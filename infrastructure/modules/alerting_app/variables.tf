variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "europe-west3"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "source_dir" {
  description = "Path to the Python source code directory"
  type        = string
}