from __future__ import annotations

from typing import Dict, List


AUTOFILLED_FIELDS = [
    "title",
    "description",
    "tags",
    "materials",
    "price",
    "quantity",
    "digital download type",
    "who made",
    "when made",
    "taxonomy id",
    "listing images",
    "digital PDF files",
]


ETSY_REVIEW_CHECKLIST = [
    "Open Etsy Shop Manager and go to Listings > Drafts.",
    "Open the newly created draft listing.",
    "Review title, description, tags, price, photos, and digital files directly in Etsy.",
    "Confirm Etsy taxonomy/category is correct for the product.",
    "Confirm all listing photos are uploaded and in the order you want.",
    "Confirm the digital PDF files are attached.",
    "Only publish manually in Etsy when you are satisfied.",
]


def build_etsy_review_handoff(draft_payload: Dict[str, object], listing_response: Dict[str, object], uploads: Dict[str, object]) -> Dict[str, object]:
    listing_id = listing_response.get("listing_id")
    return {
        "review_surface": "etsy_draft_listing",
        "listing_id": listing_id,
        "state": listing_response.get("state", "draft"),
        "open_in_etsy": "Open Etsy Shop Manager > Listings > Drafts, then open this draft listing.",
        "possible_listing_url": _response_url(listing_response),
        "autofilled_fields": AUTOFILLED_FIELDS,
        "review_checklist": ETSY_REVIEW_CHECKLIST,
        "publish_policy": {
            "auto_publish": False,
            "manual_publish_required": True,
            "message": "The bot creates a draft only. Final approval and publishing happen inside Etsy.",
        },
        "uploaded_assets": {
            "listing_image_count": len(list(uploads.get("listing_images", []))),
            "digital_file_count": len(list(uploads.get("digital_files", []))),
        },
        "listing_snapshot": {
            "title": draft_payload.get("title"),
            "price": draft_payload.get("price"),
            "tags": draft_payload.get("tags", []),
        },
    }


def _response_url(listing_response: Dict[str, object]) -> str:
    for key in ["url", "edit_url", "listing_url"]:
        value = listing_response.get(key)
        if value:
            return str(value)
    return ""
