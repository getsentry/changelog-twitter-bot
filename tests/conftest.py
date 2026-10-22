import os
import sys

# Terraform zips terraform/changelog-twitter-poster wholesale into the
# function's source archive, so a __pycache__ written there by importing
# main.py would change the source hash and trigger a spurious deploy. This
# runs before any test module imports main; test_startup.py passes the
# equivalent env var to its subprocesses.
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# main.py validates these at import time, so they have to exist before any
# test module imports it. Leaving SENTRY_DSN unset keeps the Sentry SDK
# disabled for the whole run.
TEST_ENV = {
    "sentrychangelog_twitter_consumer_key": "test-consumer-key",
    "sentrychangelog_twitter_consumer_secret": "test-consumer-secret",
    "sentrychangelog_twitter_access_token": "test-access-token",
    "sentrychangelog_twitter_access_token_secret": "test-access-token-secret",
    "RSS_FEED_URL": "https://example.com/changelog/feed.xml",
}

for _key, _value in TEST_ENV.items():
    os.environ.setdefault(_key, _value)
os.environ.pop("SENTRY_DSN", None)
