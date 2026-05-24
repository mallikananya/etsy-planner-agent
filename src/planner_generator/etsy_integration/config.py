from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List


DEFAULT_API_BASE_URL = "https://api.etsy.com/v3/application"


@dataclass(frozen=True)
class EtsyApiConfig:
    api_key: str
    access_token: str
    shop_id: str
    taxonomy_id: str
    price: str
    quantity: int
    api_base_url: str = DEFAULT_API_BASE_URL

    @classmethod
    def from_env(cls) -> "EtsyApiConfig":
        quantity = os.environ.get("ETSY_QUANTITY", "999")
        return cls(
            api_key=os.environ.get("ETSY_API_KEY", ""),
            access_token=os.environ.get("ETSY_ACCESS_TOKEN", ""),
            shop_id=os.environ.get("ETSY_SHOP_ID", ""),
            taxonomy_id=os.environ.get("ETSY_TAXONOMY_ID", ""),
            price=os.environ.get("ETSY_PRICE", ""),
            quantity=int(quantity) if quantity.isdigit() else 0,
            api_base_url=os.environ.get("ETSY_API_BASE_URL", DEFAULT_API_BASE_URL),
        )

    def headers(self, content_type: str | None = "application/json") -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key": self.api_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def missing_fields(self, require_price: bool = True) -> List[str]:
        missing: List[str] = []
        for field_name in ["api_key", "access_token", "shop_id", "taxonomy_id"]:
            if not getattr(self, field_name):
                missing.append(field_name)
        if require_price and not self.price:
            missing.append("price")
        if self.quantity < 1:
            missing.append("quantity")
        return missing

    def validate_for_live_submission(self, require_price: bool = True) -> None:
        missing = self.missing_fields(require_price=require_price)
        if missing:
            formatted = ", ".join(missing)
            raise ValueError(f"Missing Etsy API configuration for live submission: {formatted}")
