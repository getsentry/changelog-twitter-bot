resource "google_secret_manager_secret" "secret" {
  for_each  = { for s in local.secrets : s => s }
  secret_id = each.value
  replication {
    auto {}
  }
}

locals {
  secrets = [
    "sentrychangelog_twitter_consumer_key",
    "sentrychangelog_twitter_consumer_secret",
    "sentrychangelog_twitter_access_token",
    "sentrychangelog_twitter_access_token_secret",
  ]
}
