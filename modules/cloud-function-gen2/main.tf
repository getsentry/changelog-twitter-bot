terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.23.0"
    }
  }
}

locals {
  project         = "changelog-twitter-poster"
  project_id      = "changelog-twitter-poster"
  project_num     = "157958522731"
  region          = "us-west1"
  zone            = "us-west1-b"
  bucket_location = "US-WEST1"
  cron_enabled    = var.schedule != null
}

############################
# Cloud Function resources #
############################

resource "google_service_account" "function_sa" {
  account_id   = "cf-${var.name}"
  display_name = "Cloud Function Service Account for ${var.name}"
}

resource "google_cloudfunctions2_function_iam_member" "invoker_allusers" {
  project        = google_cloudfunctions2_function.function.project
  location       = google_cloudfunctions2_function.function.location
  cloud_function = google_cloudfunctions2_function.function.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

resource "google_cloud_run_service_iam_binding" "cloud_run_invoker" {
  project  = google_cloudfunctions2_function.function.project
  location = google_cloudfunctions2_function.function.location
  service  = google_cloudfunctions2_function.function.name
  role     = "roles/run.invoker"
  members = [
    "allUsers"
  ]
}

resource "google_secret_manager_secret_iam_member" "secret_iam" {
  for_each  = { for s in var.secret_environment_variables : s.key => s }
  secret_id = each.value.secret
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.function_sa.email}"
}

resource "google_service_account_iam_member" "function_sa_actas_iam" {
  service_account_id = google_service_account.function_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.function_sa.email}"
}

resource "google_service_account_iam_member" "deploy_sa_actas_iam" {
  service_account_id = google_service_account.function_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.deploy_sa_email}"
}

resource "google_project_iam_member" "function_sa_logwriter_iam" {
  project = local.project
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}

data "archive_file" "source" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${var.temp_zip_output_dir}/${var.name}.zip"
  excludes = concat(
    tolist(fileset("${path.module}/.terragrunt-cache", "**")),
    tolist(fileset("${path.module}/.terraform", "**")),
    var.files_to_exclude,
  )
}

resource "google_storage_bucket_object" "zip" {
  source       = data.archive_file.source.output_path
  content_type = "application/zip"

  name   = "${var.source_object_prefix}${data.archive_file.source.output_md5}.zip"
  bucket = "${local.project}-cloud-function-staging"
}

resource "google_cloudfunctions2_function" "function" {
  name        = var.name
  location    = var.location
  description = var.description

  build_config {
    runtime           = var.runtime
    entry_point       = var.function_entrypoint
    docker_repository = "projects/${local.project}/locations/${var.location}/repositories/gcf-artifacts"
    source {
      storage_source {
        bucket = "${local.project}-cloud-function-staging"
        object = google_storage_bucket_object.zip.name
      }
    }
  }

  service_config {
    timeout_seconds       = var.execution_timeout
    available_memory      = var.available_memory_mb
    service_account_email = google_service_account.function_sa.email
    ingress_settings      = var.ingress_settings
    dynamic "secret_environment_variables" {
      for_each = var.secret_environment_variables
      iterator = item
      content {
        key        = item.value.key
        secret     = item.value.secret
        version    = item.value.version
        project_id = local.project
      }
    }
    environment_variables = merge(
      { LOG_EXECUTION_ID = "true" },
      var.environment_variables != null ? var.environment_variables : {},
    )
  }

  depends_on = [
    google_service_account_iam_member.function_sa_actas_iam,
    google_service_account_iam_member.deploy_sa_actas_iam,
    data.archive_file.source
  ]
}

########################
# Cron Job resources   #
########################

resource "google_service_account" "cronjob_sa" {
  count        = local.cron_enabled ? 1 : 0
  account_id   = "cj-${var.name}"
  display_name = "CronJob Service Account for ${var.name}"
  description  = "Service account for ${var.name}, owned by ${var.owner}, managed by Terraform"
}

resource "google_service_account_iam_member" "cj_deploy_sa_actas_iam" {
  count              = local.cron_enabled ? 1 : 0
  service_account_id = google_service_account.cronjob_sa[0].name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.deploy_sa_email}"
}

resource "google_cloudfunctions2_function_iam_member" "cj_cron_invoker" {
  count          = local.cron_enabled ? 1 : 0
  project        = google_cloudfunctions2_function.function.project
  location       = google_cloudfunctions2_function.function.location
  cloud_function = google_cloudfunctions2_function.function.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.cronjob_sa[0].email}"
}

resource "google_cloud_run_service_iam_member" "cj_cron_invoker" {
  count    = local.cron_enabled ? 1 : 0
  project  = google_cloudfunctions2_function.function.project
  location = google_cloudfunctions2_function.function.location
  service  = google_cloudfunctions2_function.function.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.cronjob_sa[0].email}"
}

resource "google_cloud_scheduler_job" "cron_scheduler" {
  count            = local.cron_enabled ? 1 : 0
  name             = var.name
  description      = var.description
  schedule         = var.schedule
  time_zone        = var.time_zone
  attempt_deadline = var.attempt_deadline

  http_target {
    http_method = var.http_method
    uri         = google_cloudfunctions2_function.function.url

    oidc_token {
      audience              = google_cloudfunctions2_function.function.url
      service_account_email = google_service_account.cronjob_sa[0].email
    }
  }
}
