# NOTE: terraform import is not required for services, which are idempotent on apply (do not fail if existing)
resource "google_project_service" "cloudapis_googleapis_com" {
  service = "cloudapis.googleapis.com"
}

resource "google_project_service" "cloudasset_googleapis_com" {
  service = "cloudasset.googleapis.com"
}

resource "google_project_service" "cloudbuild_googleapis_com" {
  service = "cloudbuild.googleapis.com"
}

resource "google_project_service" "cloudfunctions_googleapis_com" {
  service = "cloudfunctions.googleapis.com"
}

resource "google_project_service" "cloudscheduler_googleapis_com" {
  service = "cloudscheduler.googleapis.com"
}

resource "google_project_service" "cloudresourcemanager_googleapis_com" {
  service = "cloudresourcemanager.googleapis.com"
}

resource "google_project_service" "containerregistry_googleapis_com" {
  service = "containerregistry.googleapis.com"
}

resource "google_project_service" "iam_googleapis_com" {
  service = "iam.googleapis.com"
}

resource "google_project_service" "iamcredentials_googleapis_com" {
  service = "iamcredentials.googleapis.com"
}

resource "google_project_service" "project_service" {
  service = "iap.googleapis.com"
}

resource "google_project_service" "logging_googleapis_com" {
  service = "logging.googleapis.com"
}

resource "google_project_service" "monitoring_googleapis_com" {
  service = "monitoring.googleapis.com"
}

resource "google_project_service" "oslogin_googleapis_com" {
  service = "oslogin.googleapis.com"
}

resource "google_project_service" "run_googleapis_com" {
  service = "run.googleapis.com"
}

resource "google_project_service" "secretmanager_googleapis_com" {
  service = "secretmanager.googleapis.com"
}

resource "google_project_service" "servicemanagement_googleapis_com" {
  service = "servicemanagement.googleapis.com"
}

resource "google_project_service" "serviceusage_googleapis_com" {
  service = "serviceusage.googleapis.com"
}

resource "google_project_service" "storage_api_googleapis_com" {
  service = "storage-api.googleapis.com"
}

resource "google_project_service" "storage_component_googleapis_com" {
  service = "storage-component.googleapis.com"
}

resource "google_project_service" "storage_googleapis_com" {
  service = "storage.googleapis.com"
}

resource "google_project_service" "vpcaccess_googleapis_com" {
  service = "vpcaccess.googleapis.com"
}
