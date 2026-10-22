from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest import mock

import pytest
import requests

import main

FEED_URL = "https://example.com/changelog/feed.xml"
NOW = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)


def rss_feed(items):
    """Build an RSS 2.0 document shaped like sentry.io/changelog/feed.xml."""
    rendered = []
    for item in items:
        fields = [f"<title>{item['title']}</title>"]
        if "link" in item:
            fields.append(f"<link>{item['link']}</link>")
        if "description" in item:
            fields.append(f"<description>{item['description']}</description>")
        if "published" in item:
            fields.append(f"<pubDate>{format_datetime(item['published'])}</pubDate>")
        rendered.append("<item>" + "".join(fields) + "</item>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        "<title>Sentry Changelog</title>"
        "<link>https://sentry.io/changelog/</link>"
        "<description>What's new in Sentry</description>"
        + "".join(rendered)
        + "</channel></rss>"
    ).encode()


def atom_feed(entries):
    rendered = []
    for entry in entries:
        rendered.append(
            "<entry>"
            f"<title>{entry['title']}</title>"
            f"<link href=\"{entry['link']}\"/>"
            f"<id>{entry['link']}</id>"
            f"<updated>{entry['updated'].isoformat()}</updated>"
            f"<summary>{entry['summary']}</summary>"
            "</entry>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        "<title>Sentry Changelog</title>"
        f"<updated>{NOW.isoformat()}</updated>"
        + "".join(rendered)
        + "</feed>"
    ).encode()


def http_response(content, status_code=200):
    response = requests.Response()
    response.status_code = status_code
    response.reason = "OK" if status_code < 400 else "Error"
    response.url = FEED_URL
    response._content = content
    return response


@pytest.fixture
def frozen_now(monkeypatch):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is None else NOW.astimezone(tz)

    monkeypatch.setattr(main, "datetime", FrozenDatetime)
    return NOW


@pytest.fixture
def rss_session(monkeypatch):
    session = mock.MagicMock(spec=requests.Session)
    session.__enter__.return_value = session
    monkeypatch.setattr(main, "build_rss_session", lambda: session)
    return session


def test_returns_only_entries_published_in_the_past_hour(frozen_now, rss_session):
    rss_session.get.return_value = http_response(
        rss_feed(
            [
                {
                    "title": "Fresh",
                    "link": "https://sentry.io/changelog/fresh/",
                    "description": "Published 30 minutes ago",
                    "published": frozen_now - timedelta(minutes=30),
                },
                {
                    "title": "Stale",
                    "link": "https://sentry.io/changelog/stale/",
                    "description": "Published two hours ago",
                    "published": frozen_now - timedelta(hours=2),
                },
            ]
        )
    )

    updates = main.fetch_rss_updates(FEED_URL)

    assert updates == [
        {
            "title": "Fresh",
            "description": "Published 30 minutes ago",
            "link": "https://sentry.io/changelog/fresh/",
        }
    ]


def test_hour_boundary_is_inclusive(frozen_now, rss_session):
    rss_session.get.return_value = http_response(
        rss_feed(
            [
                {
                    "title": "Exactly one hour",
                    "link": "https://sentry.io/changelog/a/",
                    "description": "",
                    "published": frozen_now - timedelta(hours=1),
                },
                {
                    "title": "One second older",
                    "link": "https://sentry.io/changelog/b/",
                    "description": "",
                    "published": frozen_now - timedelta(hours=1, seconds=1),
                },
            ]
        )
    )

    titles = [u["title"] for u in main.fetch_rss_updates(FEED_URL)]

    assert titles == ["Exactly one hour"]


def test_converts_non_utc_publish_dates(frozen_now, rss_session):
    # 30 minutes ago, expressed in UTC-7. Naively reading the clock digits
    # would put this entry seven hours in the future.
    pacific = timezone(timedelta(hours=-7))
    rss_session.get.return_value = http_response(
        rss_feed(
            [
                {
                    "title": "Pacific",
                    "link": "https://sentry.io/changelog/pacific/",
                    "description": "",
                    "published": (frozen_now - timedelta(minutes=30)).astimezone(pacific),
                },
                {
                    "title": "Pacific stale",
                    "link": "https://sentry.io/changelog/pacific-stale/",
                    "description": "",
                    "published": (frozen_now - timedelta(minutes=90)).astimezone(pacific),
                },
            ]
        )
    )

    titles = [u["title"] for u in main.fetch_rss_updates(FEED_URL)]

    assert titles == ["Pacific"]


def test_skips_entries_without_a_date(frozen_now, rss_session):
    rss_session.get.return_value = http_response(
        rss_feed(
            [
                {"title": "Undated", "link": "https://sentry.io/changelog/undated/", "description": "x"},
                {
                    "title": "Dated",
                    "link": "https://sentry.io/changelog/dated/",
                    "description": "y",
                    "published": frozen_now - timedelta(minutes=5),
                },
            ]
        )
    )

    titles = [u["title"] for u in main.fetch_rss_updates(FEED_URL)]

    assert titles == ["Dated"]


def test_falls_back_to_updated_date_for_atom_feeds(frozen_now, rss_session):
    rss_session.get.return_value = http_response(
        atom_feed(
            [
                {
                    "title": "Atom entry",
                    "link": "https://sentry.io/changelog/atom/",
                    "summary": "From an Atom feed",
                    "updated": frozen_now - timedelta(minutes=10),
                },
                {
                    "title": "Old atom entry",
                    "link": "https://sentry.io/changelog/old-atom/",
                    "summary": "Too old",
                    "updated": frozen_now - timedelta(days=1),
                },
            ]
        )
    )

    updates = main.fetch_rss_updates(FEED_URL)

    assert updates == [
        {
            "title": "Atom entry",
            "description": "From an Atom feed",
            "link": "https://sentry.io/changelog/atom/",
        }
    ]


def test_missing_optional_fields_default_to_empty_strings(frozen_now, rss_session):
    rss_session.get.return_value = http_response(
        rss_feed([{"title": "Bare", "published": frozen_now - timedelta(minutes=1)}])
    )

    assert main.fetch_rss_updates(FEED_URL) == [{"title": "Bare", "description": "", "link": ""}]


def test_empty_feed_returns_no_updates(frozen_now, rss_session):
    rss_session.get.return_value = http_response(rss_feed([]))

    assert main.fetch_rss_updates(FEED_URL) == []


def test_fetches_feed_url_with_timeout(frozen_now, rss_session):
    rss_session.get.return_value = http_response(rss_feed([]))

    main.fetch_rss_updates(FEED_URL)

    rss_session.get.assert_called_once_with(FEED_URL, timeout=main.HTTP_TIMEOUT_SECONDS)
    rss_session.__exit__.assert_called_once()


@pytest.mark.parametrize("status_code", [403, 404, 500, 503])
def test_raises_on_persistent_http_error(frozen_now, rss_session, status_code):
    rss_session.get.return_value = http_response(b"", status_code=status_code)

    with pytest.raises(requests.HTTPError) as excinfo:
        main.fetch_rss_updates(FEED_URL)

    assert excinfo.value.response.status_code == status_code


def test_propagates_connection_errors(frozen_now, rss_session):
    rss_session.get.side_effect = requests.ConnectionError("boom")

    with pytest.raises(requests.ConnectionError):
        main.fetch_rss_updates(FEED_URL)


def test_malformed_feed_logs_a_warning_and_returns_nothing(frozen_now, rss_session, caplog):
    # Mismatched tags: feedparser flags the document as "bozo" but still
    # returns whatever it could salvage instead of raising.
    rss_session.get.return_value = http_response(
        b'<?xml version="1.0"?><rss version="2.0"><channel>'
        b"<item><title>Broken</item></channel></rss>"
    )

    updates = main.fetch_rss_updates(FEED_URL)

    assert updates == []
    assert "RSS parse warning" in caplog.text
