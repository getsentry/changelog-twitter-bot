import os
import logging
from datetime import datetime, timedelta, timezone

import feedparser
from requests_oauthlib import OAuth1Session
import sentry_sdk
from sentry_sdk.integrations.gcp import GcpIntegration

sentry_dsn = os.environ.get("SENTRY_DSN")

sentry_sdk.init(
    # changelog-twitter-poster project in sentry
    dsn=sentry_dsn,
    integrations=[
        GcpIntegration(timeout_warning=True),
    ],
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    traces_sample_rate=1.0,
)

sentrychangelog_twitter_consumer_key = os.environ.get(
    "sentrychangelog_twitter_consumer_key"
)
sentrychangelog_twitter_consumer_secret = os.environ.get(
    "sentrychangelog_twitter_consumer_secret"
)
sentrychangelog_twitter_access_token = os.environ.get(
    "sentrychangelog_twitter_access_token"
)
sentrychangelog_twitter_access_token_secret = os.environ.get(
    "sentrychangelog_twitter_access_token_secret"
)
rss_feed_url = os.environ.get("RSS_FEED_URL")


# make sure the request has all the required fields, and draft the twitter post content
def validate_component(request_json):
    if not (
        "title" in request_json
        and "description" in request_json
        and "link" in request_json
    ):
        logging.error("Component Validation: incorrect formatted webhook json")
        return False
    elif (len(request_json["title"])+len(request_json["description"])) > 280:
        # twitter allows 280 characters per post, ignore the description if it's too long
        message = "{} \n \n {}".format(
            request_json["title"],
            request_json["link"],
        )
        return message
    else:
        message = "{} \n \n {} {}".format(
            request_json["title"],
            request_json["description"],
            request_json["link"],
        )
        return message


def post_to_twitter(payload):
    oauth = OAuth1Session(
        sentrychangelog_twitter_consumer_key,
        client_secret=sentrychangelog_twitter_consumer_secret,
        resource_owner_key=sentrychangelog_twitter_access_token,
        resource_owner_secret=sentrychangelog_twitter_access_token_secret,
    )

    response = oauth.post(
        "https://api.twitter.com/2/tweets",
        json=payload,
    )

    if response.status_code != 201:
        logging.exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )
    return "Success", 200


def fetch_rss_updates(feed_url):
    """Fetch an RSS feed and return entries published within the past hour."""
    feed = feedparser.parse(feed_url)

    if feed.bozo:
        logging.error("RSS fetch failed for %s: %s", feed_url, feed.bozo_exception)
        return []

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
                    "published": entry_time,
                }
            )

    logging.info(
        "RSS feed %s: found %d entries in the past hour", feed_url, len(recent_entries)
    )
    return recent_entries


def main(request):

    # fetch the latest RSS updates
    feed_updates = fetch_rss_updates(rss_feed_url)
    print(feed_updates)
    exit(0)

    # post the updates to Twitter
    for update in feed_updates:
        message = validate_component(update)
        if message:
            post_to_twitter({"text": message})


if __name__ == "__main__":
    main()
