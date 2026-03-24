module "changelog-twitter-poster" {
  source              = "../modules/cloud-function-gen2"
  name                = "changelog-twitter-poster"
  description         = "Posting updates from https://sentry.io/changelog/ to the Sentry Changelog Twitter account"
  source_dir          = "changelog-twitter-poster"
  execution_timeout   = 120
  available_memory_mb = "128Mi"
  schedule            = "0 * * * *" # fetch new rss every hour

  environment_variables = {
    RSS_FEED_URL = "https://sentry.io/changelog/feed.xml"
    SENTRY_DSN   = "https://c11f58f9dcc1025a77ec56fc35853ee1@o1.ingest.us.sentry.io/4507657212592128"
  }

  secret_environment_variables = [
    {
      key     = "sentrychangelog_twitter_consumer_key"
      secret  = google_secret_manager_secret.secret["sentrychangelog_twitter_consumer_key"].secret_id
      version = "latest"
    },
    {
      key     = "sentrychangelog_twitter_consumer_secret"
      secret  = google_secret_manager_secret.secret["sentrychangelog_twitter_consumer_secret"].secret_id
      version = "latest"
    },
    {
      key     = "sentrychangelog_twitter_access_token"
      secret  = google_secret_manager_secret.secret["sentrychangelog_twitter_access_token"].secret_id
      version = "latest"
    },
    {
      key     = "sentrychangelog_twitter_access_token_secret"
      secret  = google_secret_manager_secret.secret["sentrychangelog_twitter_access_token_secret"].secret_id
      version = "latest"
    },
    {
      key     = "sentrychangelog_webhook_auth_header"
      secret  = google_secret_manager_secret.secret["sentrychangelog_webhook_auth_header"].secret_id
      version = "latest"
    },
  ]
}
