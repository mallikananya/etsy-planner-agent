from __future__ import annotations


ETSY_TITLE_MAX_LENGTH = 140
ETSY_TAG_MAX_COUNT = 13
ETSY_TAG_MAX_LENGTH = 20
ETSY_DESCRIPTION_MAX_LENGTH = 5000
ETSY_DIGITAL_FILE_MAX_COUNT = 5
ETSY_LISTING_IMAGE_MAX_COUNT = 10
ETSY_LISTING_IMAGE_RECOMMENDED_MIN_WIDTH = 2000


def truncate_text(value: str, max_length: int) -> str:
    value = value.strip()
    if len(value) <= max_length:
        return value
    if max_length <= 3:
        return value[:max_length]
    return value[: max_length - 3].rstrip() + "..."


def normalize_tag(value: str) -> str:
    return " ".join(value.lower().strip().split())
