from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Dict, Protocol

from planner_generator.etsy_integration.config import EtsyApiConfig


class EtsyTransport(Protocol):
    def post_json(self, url: str, headers: Dict[str, str], payload: Dict[str, object]) -> Dict[str, object]:
        ...


class UrllibEtsyTransport:
    def post_json(self, url: str, headers: Dict[str, str], payload: Dict[str, object]) -> Dict[str, object]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url=url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Etsy API request failed with status {error.code}: {body}") from error


@dataclass(frozen=True)
class EtsyDraftApiClient:
    config: EtsyApiConfig
    transport: EtsyTransport

    def create_draft_listing(self, draft_payload: Dict[str, object]) -> Dict[str, object]:
        self.config.validate_for_live_submission()
        url = f"{self.config.api_base_url}/shops/{self.config.shop_id}/listings"
        return self.transport.post_json(url, self.config.headers(), _create_listing_request(draft_payload, self.config))


def _create_listing_request(draft_payload: Dict[str, object], config: EtsyApiConfig) -> Dict[str, object]:
    return {
        "title": draft_payload["title"],
        "description": draft_payload["description"],
        "tags": draft_payload.get("tags", []),
        "materials": draft_payload.get("materials", []),
        "who_made": draft_payload.get("who_made", "i_did"),
        "when_made": draft_payload.get("when_made", "made_to_order"),
        "taxonomy_id": int(config.taxonomy_id),
        "price": config.price,
        "quantity": config.quantity,
        "type": "download",
    }
