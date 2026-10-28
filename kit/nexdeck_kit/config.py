"""The only setting a copied module asks for."""

from types import SimpleNamespace


def get_settings():
    return SimpleNamespace(resolved_secret_key=lambda: "nexdeck-workshop-kit")
