from __future__ import annotations

import json
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Protocol

from planner_generator.etsy_integration.config import EtsyApiConfig


class EtsyTransport(Protocol):
    def get_json(self, url: str, headers: Dict[str, str]) -> Dict[str, object]:
        ...

    def post_json(self, url: str, headers: Dict[str, str], payload: Dict[str, object]) -> Dict[str, object]:
        ...

    def post_form(self, url: str, headers: Dict[str, str], payload: Dict[str, str]) -> Dict[str, object]:
        ...

    def post_multipart(self, url: str, headers: Dict[str, str], fields: Dict[str, str], files: Dict[str, Path]) -> Dict[str, object]:
        ...


class UrllibEtsyTransport:
    def get_json(self, url: str, headers: Dict[str, str]) -> Dict[str, object]:
        request = urllib.request.Request(url=url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Etsy API request failed with status {error.code}: {body}") from error

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

    def post_form(self, url: str, headers: Dict[str, str], payload: Dict[str, str]) -> Dict[str, object]:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(url=url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Etsy OAuth request failed with status {error.code}: {body}") from error

    def post_multipart(self, url: str, headers: Dict[str, str], fields: Dict[str, str], files: Dict[str, Path]) -> Dict[str, object]:
        boundary = "----etsy-planner-agent-boundary"
        body = _multipart_body(boundary, fields, files)
        request_headers = dict(headers)
        request_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        request = urllib.request.Request(url=url, data=body, headers=request_headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                response_body = response.read().decode("utf-8")
                return json.loads(response_body) if response_body else {}
        except urllib.error.HTTPError as error:
            response_body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Etsy multipart request failed with status {error.code}: {response_body}") from error


@dataclass(frozen=True)
class EtsyDraftApiClient:
    config: EtsyApiConfig
    transport: EtsyTransport

    def create_draft_listing(self, draft_payload: Dict[str, object]) -> Dict[str, object]:
        self.config.validate_for_live_submission(require_price=not bool(draft_payload.get("price")))
        url = f"{self.config.api_base_url}/shops/{self.config.shop_id}/listings"
        return self.transport.post_json(url, self.config.headers(), _create_listing_request(draft_payload, self.config))

    def upload_listing_image(self, listing_id: int | str, image_path: str | Path, rank: int = 1) -> Dict[str, object]:
        self.config.validate_for_live_submission(require_price=False)
        url = f"{self.config.api_base_url}/shops/{self.config.shop_id}/listings/{listing_id}/images"
        return self.transport.post_multipart(
            url,
            self.config.headers(content_type=None),
            {"rank": str(rank)},
            {"image": Path(image_path)},
        )

    def upload_listing_file(self, listing_id: int | str, file_path: str | Path, name: str | None = None) -> Dict[str, object]:
        self.config.validate_for_live_submission(require_price=False)
        path = Path(file_path)
        url = f"{self.config.api_base_url}/shops/{self.config.shop_id}/listings/{listing_id}/files"
        return self.transport.post_multipart(
            url,
            self.config.headers(content_type=None),
            {"name": name or path.name},
            {"file": path},
        )

    def find_user_shops(self) -> Dict[str, object]:
        if not self.config.api_key or not self.config.access_token:
            raise ValueError("ETSY_API_KEY and ETSY_ACCESS_TOKEN are required to look up shops.")
        url = f"{self.config.api_base_url}/users/me/shops"
        return self.transport.get_json(url, self.config.headers())


def _create_listing_request(draft_payload: Dict[str, object], config: EtsyApiConfig) -> Dict[str, object]:
    price = config.price or str(draft_payload.get("price", ""))
    return {
        "title": draft_payload["title"],
        "description": draft_payload["description"],
        "tags": draft_payload.get("tags", []),
        "materials": draft_payload.get("materials", []),
        "who_made": draft_payload.get("who_made", "i_did"),
        "when_made": draft_payload.get("when_made", "made_to_order"),
        "taxonomy_id": int(config.taxonomy_id),
        "price": price,
        "quantity": config.quantity,
        "type": "download",
    }


def _multipart_body(boundary: str, fields: Dict[str, str], files: Dict[str, Path]) -> bytes:
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    for field_name, path in files.items():
        path = Path(path)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{field_name}"; filename="{path.name}"\r\n'.encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                path.read_bytes(),
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks)
