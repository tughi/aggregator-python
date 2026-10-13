import pytest

from aggregator import engine
from aggregator.models import Feed
from aggregator.models import db

FEEDS_QUERY = "{ feeds { id url } }"
CREATE_FEED_MUTATION = 'mutation { createFeed(url: "https://attacker.example/feed.xml") { ok } }'


@pytest.fixture(autouse=True)
def offline(fetch, no_favicons):
    fetch("https://attacker.example/feed.xml")


def test_json_query(client):
    response = client.post("/graphql", json=dict(query=FEEDS_QUERY))

    assert response.status_code == 200
    assert response.get_json() == dict(data=dict(feeds=[]))


def test_json_mutation(client):
    response = client.post("/graphql", json=dict(query=CREATE_FEED_MUTATION))

    assert response.status_code == 200
    assert response.get_json() == dict(data=dict(createFeed=dict(ok=True)))
    assert Feed.query.count() == 1


@pytest.mark.parametrize(
    "content_type",
    ["application/x-www-form-urlencoded", "multipart/form-data", "text/plain"],
    ids=["urlencoded-form", "multipart-form", "text-plain"],
)
def test_rejects_bodies_that_forms_can_send(client, content_type):
    # The body types a cross-site <form> can submit without a CORS preflight
    response = client.post("/graphql", data=dict(query=CREATE_FEED_MUTATION), content_type=content_type)

    assert response.status_code == 415
    assert Feed.query.count() == 0


@pytest.mark.parametrize("sec_fetch_site", ["cross-site", "same-site"])
def test_rejects_requests_from_other_sites(client, sec_fetch_site):
    response = client.post("/graphql", json=dict(query=CREATE_FEED_MUTATION), headers={"Sec-Fetch-Site": sec_fetch_site})

    assert response.status_code == 403
    assert Feed.query.count() == 0


@pytest.mark.parametrize("sec_fetch_site", ["same-origin", "none", None], ids=["same-origin", "typed-by-user", "header-missing"])
def test_accepts_requests_from_same_origin(client, sec_fetch_site):
    headers = {"Sec-Fetch-Site": sec_fetch_site} if sec_fetch_site else {}

    response = client.post("/graphql", json=dict(query=FEEDS_QUERY), headers=headers)

    assert response.status_code == 200


def test_rejects_mutations_over_get(client):
    response = client.get("/graphql", query_string=dict(query=CREATE_FEED_MUTATION))

    assert response.status_code == 405
    assert Feed.query.count() == 0


def test_create_feed_rejects_urls_that_are_not_web_urls(client):
    response = client.post("/graphql", json=dict(query='mutation { createFeed(url: "file:///etc/passwd") { ok } }'))

    assert [error["message"] for error in response.get_json()["errors"]] == [engine.NOT_A_WEB_URL_MESSAGE]
    assert Feed.query.count() == 0


def test_update_feed_rejects_urls_that_are_not_web_urls(client):
    client.post("/graphql", json=dict(query=CREATE_FEED_MUTATION))
    feed = Feed.query.one()

    response = client.post("/graphql", json=dict(query='mutation { updateFeed(id: %d, url: "file:///etc/passwd") { ok } }' % feed.id))

    assert [error["message"] for error in response.get_json()["errors"]] == [engine.NOT_A_WEB_URL_MESSAGE]
    assert db.session.get(Feed, feed.id).url == "https://attacker.example/feed.xml"
