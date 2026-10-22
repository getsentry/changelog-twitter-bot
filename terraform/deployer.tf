###################################
# Terraform apply service account #
###################################

# The apply account (var.terraformer) lives in the sac-prod-sa project. Its
# access to the state bucket (sac-prod-tf--changelog-x) is managed there;
# everything it needs inside this project is granted here. These grants must
# be bootstrapped once by a human with Owner on the project. Because the
# projectIamAdmin grant below is conditioned to a short list of roles, the
# account cannot change its own roles or the plan account's (planner.tf): any
# later edit to either file needs a human to apply it, after which the CI
# apply is a no-op.

locals {
  deploy_sa_email  = var.terraformer
  deploy_sa_member = "serviceAccount:${local.deploy_sa_email}"

  # Narrowest predefined role per resource type this configuration manages.
  # The *_iam_member resources need setIamPolicy, which only the admin roles
  # carry (verified 2026-10-22: neither cloudfunctions.developer nor
  # run.developer includes it). secretmanager.admin cannot read secret values
  # (that is secretAccessor), and iam.serviceAccountAdmin cannot create keys
  # or impersonate.
  deploy_sa_project_roles = [
    "roles/cloudfunctions.admin",           # google_cloudfunctions2_function + its IAM bindings
    "roles/run.admin",                      # google_cloud_run_service_iam_member on the gen2 service
    "roles/cloudscheduler.admin",           # google_cloud_scheduler_job
    "roles/secretmanager.admin",            # google_secret_manager_secret + its IAM bindings
    "roles/iam.serviceAccountAdmin",        # google_service_account + google_service_account_iam_member
    "roles/serviceusage.serviceUsageAdmin", # google_project_service
  ]

  # Project-level roles the deployer is allowed to grant or revoke: the
  # function and build SAs' logWriter bindings, and the build SA's push access
  # to the gcf-artifacts repository.
  deploy_sa_grantable_roles = [
    "roles/logging.logWriter",
    "roles/artifactregistry.writer",
  ]
}

resource "google_project_iam_member" "deploy_sa" {
  for_each = toset(local.deploy_sa_project_roles)
  project  = local.project
  role     = each.value
  member   = local.deploy_sa_member
}

# Unconditioned, projectIamAdmin could grant Owner to anyone, which would make
# every other role on this list irrelevant. The condition restricts setIamPolicy
# calls to the listed roles; getIamPolicy is unaffected so plans still work.
resource "google_project_iam_member" "deploy_sa_project_iam_admin" {
  project = local.project
  role    = "roles/resourcemanager.projectIamAdmin"
  member  = local.deploy_sa_member

  condition {
    title       = "deployer-restricted-role-grants"
    description = "Deployer may only grant or revoke: ${join(", ", local.deploy_sa_grantable_roles)}"
    # NOTE: edits to this condition must be applied by a human; the deployer
    # cannot modify its own projectIamAdmin binding.
    expression = "api.getAttribute('iam.googleapis.com/modifiedGrantsByRole', []).hasOnly(${jsonencode(local.deploy_sa_grantable_roles)})"
  }
}

# Uploading source archives and updating bucket settings. Scoped to the one
# bucket rather than project-wide storage.admin; creating the bucket from
# scratch still needs a human bootstrap.
resource "google_storage_bucket_iam_member" "deploy_sa_staging_bucket" {
  bucket = google_storage_bucket.staging_bucket.name
  role   = "roles/storage.admin"
  member = local.deploy_sa_member
}

# The module grants the build SA read access on the Google-managed source
# bucket; the deployer needs to be able to set IAM on that bucket to manage
# the binding. legacyBucketOwner is the narrowest predefined role that carries
# buckets.setIamPolicy; unlike storage.admin it cannot read object contents.
resource "google_storage_bucket_iam_member" "deploy_sa_gcf_sources_bucket" {
  bucket = module.changelog-twitter-poster.gcf_sources_bucket
  role   = "roles/storage.legacyBucketOwner"
  member = local.deploy_sa_member
}
