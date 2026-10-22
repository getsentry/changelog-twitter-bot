import pytest

import main

TITLE = "New Feature: Faster Issue Search"
DESCRIPTION = "Issue search is now twice as fast across all projects."
LINK = "https://sentry.io/changelog/faster-issue-search/"


def test_includes_description_when_it_fits():
    message = main.validate_component(
        {"title": TITLE, "description": DESCRIPTION, "link": LINK}
    )

    assert message == f"{TITLE}\n\n{DESCRIPTION} {LINK}"
    assert len(message) <= main.TWEET_MAX_LENGTH


def test_strips_surrounding_whitespace():
    message = main.validate_component(
        {"title": f"  {TITLE}\n", "description": f"\t{DESCRIPTION}  ", "link": f" {LINK} "}
    )

    assert message == f"{TITLE}\n\n{DESCRIPTION} {LINK}"


def test_drops_description_when_full_message_is_too_long():
    long_description = "x" * 300

    message = main.validate_component(
        {"title": TITLE, "description": long_description, "link": LINK}
    )

    assert message == f"{TITLE}\n\n{LINK}"
    assert long_description not in message


def test_keeps_description_at_exactly_the_limit():
    # title + separator + description + space + link == 280
    fixed = len(TITLE) + len(main.SEPARATOR) + 1 + len(LINK)
    description = "d" * (main.TWEET_MAX_LENGTH - fixed)

    message = main.validate_component(
        {"title": TITLE, "description": description, "link": LINK}
    )

    assert len(message) == main.TWEET_MAX_LENGTH
    assert description in message


def test_drops_description_one_char_over_the_limit():
    fixed = len(TITLE) + len(main.SEPARATOR) + 1 + len(LINK)
    description = "d" * (main.TWEET_MAX_LENGTH - fixed + 1)

    message = main.validate_component(
        {"title": TITLE, "description": description, "link": LINK}
    )

    assert message == f"{TITLE}\n\n{LINK}"


def test_rejects_when_title_and_link_alone_exceed_the_limit(caplog):
    long_title = "t" * 300

    result = main.validate_component(
        {"title": long_title, "description": "", "link": LINK}
    )

    assert result is False
    assert "Tweet too long" in caplog.text


def test_allows_empty_description():
    message = main.validate_component({"title": TITLE, "description": "", "link": LINK})

    assert message
    assert message.startswith(TITLE)
    assert message.endswith(LINK)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": TITLE},
        {"title": TITLE, "description": DESCRIPTION},
        {"description": DESCRIPTION, "link": LINK},
        {"title": TITLE, "link": LINK},
    ],
    ids=["empty", "title-only", "no-link", "no-title", "no-description"],
)
def test_rejects_payload_missing_required_keys(payload, caplog):
    assert main.validate_component(payload) is False
    assert "incorrect formatted webhook json" in caplog.text


@pytest.mark.parametrize(
    "title, link",
    [("", LINK), ("   ", LINK), (TITLE, ""), (TITLE, "  \n"), ("", "")],
    ids=["empty-title", "blank-title", "empty-link", "blank-link", "both-empty"],
)
def test_rejects_empty_title_or_link(title, link, caplog):
    assert main.validate_component({"title": title, "description": DESCRIPTION, "link": link}) is False
    assert "title or link is empty" in caplog.text
