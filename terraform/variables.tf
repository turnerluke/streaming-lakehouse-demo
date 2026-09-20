variable "project_id" {
  type        = string
  description = "GCP project id. Create the project + link billing in the console before applying."
}

variable "region" {
  type    = string
  default = "US"
}
