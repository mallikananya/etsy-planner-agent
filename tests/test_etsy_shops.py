import json

from planner_generator.etsy_integration.api import EtsyDraftApiClient
from planner_generator.etsy_integration.config import EtsyApiConfig
from planner_generator.etsy_integration.shops import env_line_for_shop, lookup_shop


class FakeShopTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get_json(self, url, headers):
        self.calls.append({"url": url, "headers": headers})
        return self.response

    def post_json(self, url, headers, payload):
        raise AssertionError("Shop lookup should not create resources.")

    def post_form(self, url, headers, payload):
        raise AssertionError("Shop lookup should not use OAuth form posts.")

    def post_multipart(self, url, headers, fields, files):
        raise AssertionError("Shop lookup should not upload files.")


def test_lookup_shop_selects_first_shop_and_writes_env_line(tmp_path):
    transport = FakeShopTransport({"results": [{"shop_id": 111, "shop_name": "Planner One"}]})
    client = EtsyDraftApiClient(config=_config(), transport=transport)

    result = lookup_shop(output_path=tmp_path / "shop.json", api_client=client)
    saved = json.loads(result.output_path.read_text(encoding="utf-8"))

    assert saved["shop_id"] == 111
    assert env_line_for_shop(result.shop) == "ETSY_SHOP_ID=111"
    assert transport.calls[0]["url"].endswith("/users/me/shops")


def test_lookup_shop_can_select_by_name(tmp_path):
    transport = FakeShopTransport(
        {
            "results": [
                {"shop_id": 111, "shop_name": "Planner One"},
                {"shop_id": 222, "shop_name": "Planner Two"},
            ]
        }
    )
    client = EtsyDraftApiClient(config=_config(), transport=transport)

    result = lookup_shop(output_path=tmp_path / "shop.json", shop_name="Planner Two", api_client=client)

    assert result.shop["shop_id"] == 222


def _config() -> EtsyApiConfig:
    return EtsyApiConfig(
        api_key="api-key",
        access_token="access-token",
        shop_id="",
        taxonomy_id="",
        price="",
        quantity=999,
    )
