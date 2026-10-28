"""What the tools ask of GitHub, behind one small class, so that the tests put a stand-in in its place.

Reads and the one write that must happen while the files are made (the discussion of a new entry) are here; the
comments and closing of issues go through ``publish.py`` after the files are pushed.
"""

from __future__ import annotations

import os
from typing import Any, Protocol

import httpx

from .common import DISCUSSION_CATEGORIES

API = "https://api.github.com"


class Hub(Protocol):
    repo: str

    def open_issues(self) -> list[dict[str, Any]]: ...

    def issue(self, number: int) -> dict[str, Any]: ...

    def comments(self, number: int) -> list[dict[str, Any]]: ...

    def post_comment(self, number: int, body: str) -> None: ...

    def close_issue(self, number: int) -> None: ...

    def create_discussion(self, title: str, body: str) -> dict[str, str] | None: ...

    def thumbs(self, discussion_id: str) -> int | None: ...


class GitHub:
    """The real thing, with the token of the action (``GITHUB_TOKEN``) and the repository (``GITHUB_REPOSITORY``)."""

    def __init__(self, repo: str | None = None, token: str | None = None) -> None:
        self.repo = repo or os.environ["GITHUB_REPOSITORY"]
        self.http = httpx.Client(
            base_url=API,
            timeout=30,
            headers={
                "Authorization": f"Bearer {token or os.environ['GITHUB_TOKEN']}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    def _pages(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        page = 1
        while True:
            answer = self.http.get(path, params={**(params or {}), "per_page": 100, "page": page})
            answer.raise_for_status()
            batch = answer.json()
            found += batch
            if len(batch) < 100:
                return found
            page += 1

    def open_issues(self) -> list[dict[str, Any]]:
        """Open issues, oldest first; pull requests are not issues here."""
        rows = self._pages(f"/repos/{self.repo}/issues", {"state": "open", "sort": "created", "direction": "asc"})
        return [row for row in rows if "pull_request" not in row]

    def issue(self, number: int) -> dict[str, Any]:
        answer = self.http.get(f"/repos/{self.repo}/issues/{number}")
        answer.raise_for_status()
        return answer.json()  # type: ignore[no-any-return]

    def comments(self, number: int) -> list[dict[str, Any]]:
        return self._pages(f"/repos/{self.repo}/issues/{number}/comments")

    def post_comment(self, number: int, body: str) -> None:
        self.http.post(f"/repos/{self.repo}/issues/{number}/comments", json={"body": body}).raise_for_status()

    def close_issue(self, number: int) -> None:
        self.http.patch(f"/repos/{self.repo}/issues/{number}", json={"state": "closed", "state_reason": "completed"}).raise_for_status()

    def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        answer = self.http.post("/graphql", json={"query": query, "variables": variables})
        answer.raise_for_status()
        body = answer.json()
        if body.get("errors"):
            raise RuntimeError(body["errors"][0].get("message", "GraphQL error"))
        return body["data"]  # type: ignore[no-any-return]

    def create_discussion(self, title: str, body: str) -> dict[str, str] | None:
        """A discussion for the thumbs; ``None`` when this repository has no discussions to put it in."""
        owner, name = self.repo.split("/", 1)
        try:
            data = self._graphql(
                "query($owner:String!,$name:String!){repository(owner:$owner,name:$name){id discussionCategories(first:25){nodes{id name}}}}",
                {"owner": owner, "name": name},
            )["repository"]
            categories = {one["name"]: one["id"] for one in data["discussionCategories"]["nodes"]}
            wanted = next((categories[name] for name in DISCUSSION_CATEGORIES if name in categories), None)
            if wanted is None and categories:
                wanted = next(iter(categories.values()))
            if wanted is None:
                return None
            made = self._graphql(
                "mutation($repo:ID!,$cat:ID!,$title:String!,$body:String!)"
                "{createDiscussion(input:{repositoryId:$repo,categoryId:$cat,title:$title,body:$body}){discussion{id url}}}",
                {"repo": data["id"], "cat": wanted, "title": title, "body": body},
            )["createDiscussion"]["discussion"]
        except (RuntimeError, httpx.HTTPError):
            return None
        return {"id": made["id"], "url": made["url"]}

    def thumbs(self, discussion_id: str) -> int | None:
        try:
            data = self._graphql(
                "query($id:ID!){node(id:$id){... on Discussion{reactionGroups{content reactors{totalCount}}}}}",
                {"id": discussion_id},
            )
        except (RuntimeError, httpx.HTTPError):
            return None
        groups = (data.get("node") or {}).get("reactionGroups") or []
        return next((int(group["reactors"]["totalCount"]) for group in groups if group["content"] == "THUMBS_UP"), 0)
