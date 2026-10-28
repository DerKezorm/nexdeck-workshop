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
PAGE = 100
#: A list longer than this many pages is not read to its end: the run fails and the next one tries again.
MAX_PAGES = 200


class Hub(Protocol):
    repo: str

    def open_issues(self, since: str | None = None) -> list[dict[str, Any]]: ...

    def comments_since(self, since: str) -> list[dict[str, Any]]: ...

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
        """Every page of a list, one after the other; a page with fewer than :data:`PAGE` rows is the last."""
        found: list[dict[str, Any]] = []
        for page in range(1, MAX_PAGES + 1):
            answer = self.http.get(path, params={**(params or {}), "per_page": PAGE, "page": page})
            answer.raise_for_status()
            batch = answer.json()
            found += batch
            if len(batch) < PAGE:
                return found
        raise RuntimeError(f"{path} has more than {MAX_PAGES} pages.")

    def open_issues(self, since: str | None = None) -> list[dict[str, Any]]:
        """Open issues, oldest first, those changed since the moment given (all when none is); pull requests are not issues here."""
        params: dict[str, Any] = {"state": "open", "sort": "created", "direction": "asc"}
        if since:
            params["since"] = since
        rows = self._pages(f"/repos/{self.repo}/issues", params)
        return [row for row in rows if "pull_request" not in row]

    def comments_since(self, since: str) -> list[dict[str, Any]]:
        """The comments of every issue and pull request of the repository that were written or changed since the moment given."""
        return self._pages(f"/repos/{self.repo}/issues/comments", {"since": since, "sort": "updated", "direction": "asc"})

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
        """A new discussion for the thumbs; ``None`` when this repository has no discussions to put it in.

        ⚠️ Never finds one by its title: the title of an entry is easy to guess, and somebody else could have made a
        discussion with it (and can rewrite it any time). The caller keeps the id of the discussion made here in
        ``entry.json``, and that id is the only way back to it.
        """
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
