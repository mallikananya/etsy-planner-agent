from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from planner_generator.etsy_integration.api import EtsyDraftApiClient, UrllibEtsyTransport
from planner_generator.etsy_integration.config import EtsyApiConfig


DEFAULT_SHOP_SELECTION_PATH = ".etsy/shop_selection.json"


@dataclass(frozen=True)
class EtsyShopLookupResult:
    output_path: Path
    shop: Dict[str, object]
    shops: List[Dict[str, object]]


def lookup_shop(
    output_path: str | Path = DEFAULT_SHOP_SELECTION_PATH,
    shop_id: str | None = None,
    shop_name: str | None = None,
    config: EtsyApiConfig | None = None,
    api_client: EtsyDraftApiClient | None = None,
) -> EtsyShopLookupResult:
    config = config or EtsyApiConfig.from_env()
    client = api_client or EtsyDraftApiClient(config=config, transport=UrllibEtsyTransport())
    response = client.find_user_shops()
    shops = _extract_shops(response)
    if not shops:
        raise ValueError("No Etsy shops were returned for the authenticated account.")
    selected = _select_shop(shops, shop_id=shop_id, shop_name=shop_name)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(selected, indent=2) + "\n", encoding="utf-8")
    return EtsyShopLookupResult(output_path=output_path, shop=selected, shops=shops)


def env_line_for_shop(shop: Dict[str, object]) -> str:
    return f"ETSY_SHOP_ID={shop['shop_id']}"


def _extract_shops(response: Dict[str, object]) -> List[Dict[str, object]]:
    if isinstance(response.get("results"), list):
        return [dict(shop) for shop in response["results"]]
    if isinstance(response.get("shops"), list):
        return [dict(shop) for shop in response["shops"]]
    if response.get("shop_id"):
        return [dict(response)]
    return []


def _select_shop(shops: List[Dict[str, object]], shop_id: str | None, shop_name: str | None) -> Dict[str, object]:
    if shop_id:
        for shop in shops:
            if str(shop.get("shop_id")) == str(shop_id):
                return shop
        raise ValueError(f"No Etsy shop matched shop_id={shop_id}.")
    if shop_name:
        normalized = shop_name.lower()
        for shop in shops:
            if str(shop.get("shop_name", "")).lower() == normalized:
                return shop
        raise ValueError(f"No Etsy shop matched shop_name={shop_name}.")
    return shops[0]
