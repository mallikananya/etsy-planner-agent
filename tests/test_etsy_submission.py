import json
from pathlib import Path

import pytest

from planner_generator.etsy_integration.api import EtsyDraftApiClient
from planner_generator.etsy_integration.config import EtsyApiConfig
from planner_generator.etsy_integration.submission import submit_etsy_draft
from planner_generator.exports.bundle_exporter import export_bundle
from planner_generator.etsy_integration.client import EtsyDraftClient
from planner_generator.theme_engine.loader import load_theme


ROOT = Path(__file__).resolve().parents[1]


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.multipart_calls = []

    def get_json(self, url, headers):
        raise AssertionError("Submission should not use shop lookup GET requests.")

    def post_json(self, url, headers, payload):
        self.calls.append({"url": url, "headers": headers, "payload": payload})
        return {"listing_id": 123456789, "state": "draft"}

    def post_form(self, url, headers, payload):
        raise AssertionError("Submission should not use OAuth form posts.")

    def post_multipart(self, url, headers, fields, files):
        self.multipart_calls.append({"url": url, "headers": headers, "fields": fields, "files": files})
        if url.endswith("/images"):
            return {"listing_image_id": len(self.multipart_calls)}
        return {"listing_file_id": len(self.multipart_calls)}


def test_etsy_config_validates_missing_live_fields():
    config = EtsyApiConfig(api_key="", access_token="", shop_id="", taxonomy_id="", price="", quantity=0)

    with pytest.raises(ValueError, match="Missing Etsy API configuration"):
        config.validate_for_live_submission()


def test_submit_etsy_draft_dry_run_writes_report(tmp_path):
    payload_path = _draft_payload_path(tmp_path)

    result = submit_etsy_draft(payload_path, tmp_path / "submission", mode="dry-run", config=_valid_config())

    assert result.output_path.exists()
    assert result.report["mode"] == "dry-run"
    assert result.report["would_create_draft_listing"] is True
    assert result.report["auto_publish"] is False


def test_live_submission_uses_mocked_etsy_transport(tmp_path):
    payload_path = _draft_payload_path(tmp_path)
    transport = FakeTransport()
    client = EtsyDraftApiClient(config=_valid_config(), transport=transport)

    result = submit_etsy_draft(payload_path, tmp_path / "submission", mode="live", config=_valid_config(), api_client=client)

    assert result.report["mode"] == "live"
    assert result.report["listing_id"] == 123456789
    assert result.report["auto_publish"] is False
    assert transport.calls[0]["url"].endswith("/shops/42/listings")
    assert transport.calls[0]["headers"]["x-api-key"] == "api-key:api-secret"
    assert transport.calls[0]["payload"]["type"] == "download"
    assert transport.calls[0]["payload"]["taxonomy_id"] == 1234
    assert len(transport.multipart_calls) == 12
    assert "/images" in transport.multipart_calls[0]["url"]
    assert "/files" in transport.multipart_calls[-1]["url"]
    assert result.report["uploads"]["listing_images"]
    assert result.report["uploads"]["digital_files"]
    handoff = result.report["etsy_review_handoff"]
    assert handoff["review_surface"] == "etsy_draft_listing"
    assert handoff["publish_policy"]["manual_publish_required"] is True
    assert handoff["publish_policy"]["auto_publish"] is False
    assert "title" in handoff["autofilled_fields"]
    assert "price" in handoff["autofilled_fields"]
    assert "digital PDF files" in handoff["autofilled_fields"]
    assert handoff["uploaded_assets"]["listing_image_count"] == 10
    assert handoff["uploaded_assets"]["digital_file_count"] == 2


def test_live_submission_autofills_generated_price_when_env_price_is_blank(tmp_path):
    payload_path = _draft_payload_path(tmp_path)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert payload["price"]
    transport = FakeTransport()
    config = EtsyApiConfig(
        api_key="api-key",
        access_token="access-token",
        shop_id="42",
        taxonomy_id="1234",
        price="",
        quantity=999,
        api_secret="api-secret",
    )
    client = EtsyDraftApiClient(config=config, transport=transport)

    submit_etsy_draft(payload_path, tmp_path / "submission", mode="live", config=config, api_client=client)

    assert transport.calls[0]["payload"]["price"] == payload["price"]


def _draft_payload_path(tmp_path: Path) -> Path:
    theme = load_theme(ROOT / "themes/minimal_neutral.json")
    export = export_bundle(ROOT / "specs/bundles/component_showcase.json", theme, tmp_path / "export")
    draft = EtsyDraftClient().create_draft_plan(export.manifest_path, export.output_dir / "listing")
    payload = json.loads(draft.output_path.read_text(encoding="utf-8"))
    assert payload["state"] == "draft"
    return draft.output_path


def _valid_config() -> EtsyApiConfig:
    return EtsyApiConfig(
        api_key="api-key",
        access_token="access-token",
        shop_id="42",
        taxonomy_id="1234",
        price="9.99",
        quantity=999,
        api_secret="api-secret",
    )
