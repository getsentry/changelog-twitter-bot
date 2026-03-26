import os
import logging
from datetime import datetime, timedelta, timezone

import requests
import feedparser
from requests_oauthlib import OAuth1Session
import sentry_sdk
from sentry_sdk.integrations.gcp import GcpIntegration

HTTP_TIMEOUT_SECONDS = 10

REQUIRED_ENV_VARS = [
    "sentrychangelog_twitter_consumer_key",
    "sentrychangelog_twitter_consumer_secret",
    "sentrychangelog_twitter_access_token",
    "sentrychangelog_twitter_access_token_secret",
    "RSS_FEED_URL",
]

for _var in REQUIRED_ENV_VARS:
    if not os.environ.get(_var):
        raise EnvironmentError(f"Missing required environment variable: {_var}")

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    integrations=[
        GcpIntegration(timeout_warning=True),
    ],
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    traces_sample_rate=1.0,
)

sentrychangelog_twitter_consumer_key = os.environ["sentrychangelog_twitter_consumer_key"]
sentrychangelog_twitter_consumer_secret = os.environ["sentrychangelog_twitter_consumer_secret"]
sentrychangelog_twitter_access_token = os.environ["sentrychangelog_twitter_access_token"]
sentrychangelog_twitter_access_token_secret = os.environ["sentrychangelog_twitter_access_token_secret"]
rss_feed_url = os.environ["RSS_FEED_URL"]


TWEET_MAX_LENGTH = 280
SEPARATOR = "\n\n"


def validate_component(request_json):
    """Validate required fields and build a tweet that fits within the character limit."""
    required_keys = ("title", "description", "link")
    if not all(k in request_json for k in required_keys):
        logging.error("Component Validation: incorrect formatted webhook json")
        return False

    title = request_json["title"].strip()
    description = request_json["description"].strip()
    link = request_json["link"].strip()

    if not title or not link:
        logging.error("Component Validation: title or link is empty")
        return False

    full_message = f"{title}{SEPARATOR}{description} {link}"
    if len(full_message) <= TWEET_MAX_LENGTH:
        return full_message

    short_message = f"{title}{SEPARATOR}{link}"
    if len(short_message) <= TWEET_MAX_LENGTH:
        return short_message

    logging.warning("Tweet too long even without description (%d chars), skipping", len(short_message))
    return False


def post_to_twitter(oauth, payload):
    response = oauth.post(
        "https://api.twitter.com/2/tweets",
        json=payload,
        timeout=HTTP_TIMEOUT_SECONDS,
    )

    if response.status_code != 201:
        error_msg = f"Twitter API error: {response.status_code} {response.text}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)


def fetch_rss_updates(feed_url):
    """Fetch an RSS feed and return entries published within the past hour."""
    response = requests.get(feed_url, timeout=HTTP_TIMEOUT_SECONDS)
    response.raise_for_status()
    feed = feedparser.parse(response.content)

    if feed.bozo:
        logging.warning("RSS parse warning for %s: %s", feed_url, feed.bozo_exception)

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_entries = []

    for entry in feed.entries:
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if not published:
            continue

        entry_time = datetime(*published[:6], tzinfo=timezone.utc)
        if entry_time >= one_hour_ago:
            recent_entries.append(
                {
                    "title": entry.get("title", ""),
                    "description": entry.get("summary", ""),
                    "link": entry.get("link", ""),
                }
            )

    logging.info(
        "RSS feed %s: found %d entries in the past hour", feed_url, len(recent_entries)
    )
    return recent_entries


def main(request):

    # fetch the latest RSS updates
    feed_updates = fetch_rss_updates(rss_feed_url)

    if not feed_updates:
        return "No updates found", 200

    oauth = OAuth1Session(
        sentrychangelog_twitter_consumer_key,
        client_secret=sentrychangelog_twitter_consumer_secret,
        resource_owner_key=sentrychangelog_twitter_access_token,
        resource_owner_secret=sentrychangelog_twitter_access_token_secret,
    )

    posted = 0
    errors = 0
    for update in feed_updates:
        message = validate_component(update)
        if not message:
            continue
        try:
            post_to_twitter(oauth, {"text": message})
            posted += 1
        except Exception:
            errors += 1
            logging.exception("Failed to post tweet for: %s", update.get("title", ""))
            sentry_sdk.capture_exception()

    summary = f"Posted {posted} tweets, {errors} failed"
    if errors:
        logging.warning(summary)
    return summary, 200


if __name__ == "__main__":
    main(None)
