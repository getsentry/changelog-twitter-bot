variable "terraformer" {
  description = "Terraform apply service account email — has write permissions, used by tf-apply.yaml on push to main and for local applies"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]@[a-z][a-z0-9-]+\\.iam\\.gserviceaccount\\.com$", var.terraformer))
    error_message = "terraformer must be a valid GCP service account email ending in .iam.gserviceaccount.com"
  }
}

variable "terraformer_plan" {
  description = "Terraform plan service account email — read-only, used by tf-plan.yaml on pull requests"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]@[a-z][a-z0-9-]+\\.iam\\.gserviceaccount\\.com$", var.terraformer_plan))
    error_message = "terraformer_plan must be a valid GCP service account email ending in .iam.gserviceaccount.com"
  }
}
