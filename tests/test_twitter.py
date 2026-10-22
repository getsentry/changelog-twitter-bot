from unittest import mock

import pytest
from requests.adapters import HTTPAdapter

import main


def twitter_response(status_code, text=""):
    response = mock.Mock()
    response.status_code = status_code
    response.text = text
    return response


def test_posts_payload_to_tweets_endpoint():
    oauth = mock.Mock()
    oauth.post.return_value = twitter_response(201)

    main.post_to_twitter(oauth, {"text": "hello"})

    oauth.post.assert_called_once_with(
        "https://api.twitter.com/2/tweets",
        json={"text": "hello"},
        timeout=main.HTTP_TIMEOUT_SECONDS,
    )


@pytest.mark.parametrize("status_code", [200, 400, 401, 403, 429, 500])
def test_raises_when_twitter_does_not_return_201(status_code, caplog):
    oauth = mock.Mock()
    oauth.post.return_value = twitter_response(status_code, '{"detail": "nope"}')

    with pytest.raises(RuntimeError) as excinfo:
        main.post_to_twitter(oauth, {"text": "hello"})

    message = str(excinfo.value)
    assert str(status_code) in message
    assert '{"detail": "nope"}' in message
    assert "Twitter API error" in caplog.text


def test_rss_session_sets_user_agent():
    with main.build_rss_session() as session:
        assert session.headers["User-Agent"] == main.USER_AGENT
        assert "changelog-twitter-bot" in session.headers["User-Agent"]


@pytest.mark.parametrize("url", ["https://sentry.io/changelog/feed.xml", "http://example.com/feed"])
def test_rss_session_retries_transient_failures(url):
    with main.build_rss_session() as session:
        adapter = session.get_adapter(url)

    assert isinstance(adapter, HTTPAdapter)
    retry = adapter.max_retries
    assert retry.total == main.RSS_FETCH_RETRIES
    assert retry.backoff_factor == main.RSS_FETCH_BACKOFF_FACTOR
    assert set(retry.status_forcelist) == set(main.RSS_FETCH_RETRY_STATUSES)
    assert retry.allowed_methods == frozenset(["GET"])
    # The function has a 120s budget, so a server-supplied Retry-After must
    # not be allowed to stretch the wait indefinitely.
    assert retry.respect_retry_after_header is False
    # Exhausted retries return the final response so raise_for_status()
    # surfaces the real HTTP error rather than a MaxRetryError.
    assert retry.raise_on_status is False
