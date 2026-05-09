from __future__ import annotations


class EtsyDraftClient:
    """Boundary for future Etsy draft listing integration."""

    def create_draft_listing(self, bundle_manifest_path: str) -> None:
        raise NotImplementedError("Etsy draft listing creation is planned for a later phase.")
