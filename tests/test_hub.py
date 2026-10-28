"""The GitHub client against a stand-in server: discussions for the thumbs, and their count."""

from __future__ import annotations

import json
from typing import Any

import httpx

from tools.hub import GitHub


def _hub(handler: Any) -> GitHub:
    hub = GitHub("DerKezorm/nexdeck-workshop", "token-for-tests")
    hub.http = httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(handler))
    return hub


class Server:
    def __init__(self, categories: list[str], titles: list[str] | None = None) -> None:
        self.categories = categories
        self.titles = titles or []
        self.made: list[dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["query"]
        variables = json.loads(request.content)["variables"]
        if "discussionCategories" in query:
            nodes = [{"id": f"C_{index}", "name": name} for index, name in enumerate(self.categories)]
            return httpx.Response(200, json={"data": {"repository": {"id": "R_1", "discussionCategories": {"nodes": nodes}}}})
        if "discussions(first:100" in query:
            nodes = [{"id": f"D_old{index}", "url": f"https://x/{index}", "title": title} for index, title in enumerate(self.titles)]
            return httpx.Response(200, json={"data": {"repository": {"discussions": {"nodes": nodes, "pageInfo": {"hasNextPage": False, "endCursor": None}}}}})
        if "createDiscussion" in query:
            self.made.append(variables)
            return httpx.Response(200, json={"data": {"createDiscussion": {"discussion": {"id": "D_new", "url": "https://x/new"}}}})
        if "reactionGroups" in query:
            groups = [{"content": "HEART", "reactors": {"totalCount": 9}}, {"content": "THUMBS_UP", "reactors": {"totalCount": 3}}]
            return httpx.Response(200, json={"data": {"node": {"reactionGroups": groups}}})
        return httpx.Response(404)


def test_karten13_ac6_the_discussion_goes_into_the_cards_category_when_there_is_one() -> None:
    server = Server(["General", "Show and tell", "Cards"])
    made = _hub(server).create_discussion("Queue (1/queue)", "Body")
    assert made == {"id": "D_new", "url": "https://x/new"}
    assert server.made[0]["cat"] == "C_2" and server.made[0]["repo"] == "R_1" and server.made[0]["title"] == "Queue (1/queue)"


def test_karten13_ac6_without_a_cards_category_the_next_best_one_is_taken() -> None:
    server = Server(["General", "Q&A", "Show and tell"])
    _hub(server).create_discussion("Queue (1/queue)", "Body")
    assert server.made[0]["cat"] == "C_2"


def test_karten13_ac6_a_discussion_with_the_title_is_not_made_twice() -> None:
    server = Server(["Cards"], titles=["Other (2/other)", "Queue (1/queue)"])
    assert _hub(server).create_discussion("Queue (1/queue)", "Body") == {"id": "D_old1", "url": "https://x/1"}
    assert server.made == []


def test_karten13_ac6_a_repository_without_discussions_gives_none() -> None:
    assert _hub(Server([])).create_discussion("Queue (1/queue)", "Body") is None


def test_karten13_ac6_only_the_thumbs_up_are_counted() -> None:
    assert _hub(Server([])).thumbs("D_1") == 3
