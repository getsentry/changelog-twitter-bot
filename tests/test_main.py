from unittest import mock

import pytest

import main

VALID_UPDATE = {
    "title": "Session Replay for Mobile",
    "description": "Replay is now available on iOS and Android.",
    "link": "https://sentry.io/changelog/session-replay-mobile/",
}
ANOTHER_UPDATE = {
    "title": "New Alert Rules",
    "description": "Alert on anything.",
    "link": "https://sentry.io/changelog/new-alert-rules/",
}
INVALID_UPDATE = {"title": "", "description": "No title here", "link": "https://sentry.io/x/"}


@pytest.fixture
def fetch_rss_updates(monkeypatch):
    fetch = mock.Mock(return_value=[])
    monkeypatch.setattr(main, "fetch_rss_updates", fetch)
    return fetch


@pytest.fixture
def oauth_session(monkeypatch):
    oauth_cls = mock.Mock()
    monkeypatch.setattr(main, "OAuth1Session", oauth_cls)
    return oauth_cls


@pytest.fixture
def post_to_twitter(monkeypatch):
    post = mock.Mock(return_value=None)
    monkeypatch.setattr(main, "post_to_twitter", post)
    return post


@pytest.fixture
def capture_exception(monkeypatch):
    capture = mock.Mock()
    monkeypatch.setattr(main.sentry_sdk, "capture_exception", capture)
    return capture


def test_fetches_the_configured_feed(fetch_rss_updates, oauth_session, post_to_twitter):
    main.main(None)

    fetch_rss_updates.assert_called_once_with(main.rss_feed_url)


def test_no_updates_posts_nothing(fetch_rss_updates, oauth_session, post_to_twitter):
    result = main.main(None)

    assert result == ("No updates found", 200)
    oauth_session.assert_not_called()
    post_to_twitter.assert_not_called()


def test_posts_each_valid_update(fetch_rss_updates, oauth_session, post_to_twitter):
    fetch_rss_updates.return_value = [VALID_UPDATE, ANOTHER_UPDATE]

    result = main.main(None)

    assert result == ("Posted 2 tweets, 0 failed", 200)
    oauth = oauth_session.return_value
    assert post_to_twitter.call_args_list == [
        mock.call(oauth, {"text": main.validate_component(VALID_UPDATE)}),
        mock.call(oauth, {"text": main.validate_component(ANOTHER_UPDATE)}),
    ]


def test_skips_updates_that_fail_validation(fetch_rss_updates, oauth_session, post_to_twitter):
    fetch_rss_updates.return_value = [INVALID_UPDATE, VALID_UPDATE]

    result = main.main(None)

    assert result == ("Posted 1 tweets, 0 failed", 200)
    post_to_twitter.assert_called_once_with(
        oauth_session.return_value, {"text": main.validate_component(VALID_UPDATE)}
    )


def test_only_invalid_updates_posts_nothing(fetch_rss_updates, oauth_session, post_to_twitter):
    fetch_rss_updates.return_value = [INVALID_UPDATE]

    result = main.main(None)

    assert result == ("Posted 0 tweets, 0 failed", 200)
    post_to_twitter.assert_not_called()


def test_a_failed_post_is_reported_and_does_not_stop_the_rest(
    fetch_rss_updates, oauth_session, post_to_twitter, capture_exception, caplog
):
    fetch_rss_updates.return_value = [VALID_UPDATE, ANOTHER_UPDATE]
    post_to_twitter.side_effect = [RuntimeError("Twitter API error: 403 forbidden"), None]

    result = main.main(None)

    assert result == ("Posted 1 tweets, 1 failed", 200)
    assert post_to_twitter.call_count == 2
    capture_exception.assert_called_once()
    assert "Failed to post tweet for: Session Replay for Mobile" in caplog.text
    assert "Posted 1 tweets, 1 failed" in caplog.text


def test_authenticates_with_the_configured_credentials(
    fetch_rss_updates, oauth_session, post_to_twitter
):
    fetch_rss_updates.return_value = [VALID_UPDATE]

    main.main(None)

    oauth_session.assert_called_once_with(
        main.sentrychangelog_twitter_consumer_key,
        client_secret=main.sentrychangelog_twitter_consumer_secret,
        resource_owner_key=main.sentrychangelog_twitter_access_token,
        resource_owner_secret=main.sentrychangelog_twitter_access_token_secret,
    )


def test_feed_fetch_failure_propagates(fetch_rss_updates, oauth_session, post_to_twitter):
    fetch_rss_updates.side_effect = RuntimeError("feed down")

    with pytest.raises(RuntimeError, match="feed down"):
        main.main(None)

    oauth_session.assert_not_called()
