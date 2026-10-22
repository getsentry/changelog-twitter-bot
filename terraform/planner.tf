##################################
# Terraform plan service account #
##################################

# Read-only account used by tf-plan.yaml on pull requests. It refreshes every
# resource in state but never writes, so it gets a single custom role holding
# only get/list/getIamPolicy permissions, one group per resource type this
# configuration manages. Its read access to the state bucket is managed in the
# sac-prod project.
#
# Creating or changing the custom role needs iam.roles.create/update, which
# the apply account does not hold; apply changes to this file as a human.

locals {
  plan_sa_member = "serviceAccount:${var.terraformer_plan}"
}

resource "google_project_iam_custom_role" "tf_plan_reader" {
  role_id     = "changelogXTfPlanReader"
  title       = "Changelog X TF Plan Reader"
  description = "Read-only refresh of every resource managed by the changelog-twitter-poster Terraform configuration."
  project     = local.project
  permissions = [
    # Project (provider setup and google_project_iam_member drift)
    "resourcemanager.projects.get",
    "resourcemanager.projects.getIamPolicy",
    # google_project_service
    "serviceusage.services.get",
    "serviceusage.services.list",
    # google_cloudfunctions2_function + google_cloudfunctions2_function_iam_member
    "cloudfunctions.functions.get",
    "cloudfunctions.functions.list",
    "cloudfunctions.functions.getIamPolicy",
    # google_cloud_run_service_iam_member on the gen2 service
    "run.services.get",
    "run.services.list",
    "run.services.getIamPolicy",
    # google_cloud_scheduler_job
    "cloudscheduler.jobs.get",
    "cloudscheduler.jobs.list",
    # google_secret_manager_secret + google_secret_manager_secret_iam_member
    # (metadata only; versions.access is deliberately absent)
    "secretmanager.secrets.get",
    "secretmanager.secrets.list",
    "secretmanager.secrets.getIamPolicy",
    # google_service_account + google_service_account_iam_member
    "iam.serviceAccounts.get",
    "iam.serviceAccounts.list",
    "iam.serviceAccounts.getIamPolicy",
    # google_project_iam_custom_role (this role)
    "iam.roles.get",
    "iam.roles.list",
    # google_storage_bucket, google_storage_bucket_iam_member,
    # google_storage_bucket_object (metadata only)
    "storage.buckets.get",
    "storage.buckets.getIamPolicy",
    "storage.objects.get",
    "storage.objects.list",
  ]
}

resource "google_project_iam_member" "plan_sa_reader" {
  project = local.project
  role    = google_project_iam_custom_role.tf_plan_reader.id
  member  = local.plan_sa_member
}
