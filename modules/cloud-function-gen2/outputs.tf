output "function_name" {
  value = google_cloudfunctions2_function.function.name
}

output "function_project" {
  value = google_cloudfunctions2_function.function.project
}

output "function_region" {
  value = google_cloudfunctions2_function.function.location
}

output "function_trigger_url" {
  value = google_cloudfunctions2_function.function.url
}

output "function_sa_email" {
  value = google_service_account.function_sa.email
}

output "build_sa_email" {
  value = google_service_account.build_sa.email
}

output "gcf_sources_bucket" {
  value = local.gcf_sources_bucket
}

output "cronjob_sa_email" {
  value = local.cron_enabled ? google_service_account.cronjob_sa[0].email : null
}
