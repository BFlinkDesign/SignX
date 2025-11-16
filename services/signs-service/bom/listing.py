from __future__ import annotations


def infer_listing_category(illumination: str) -> str | None:
    if illumination == "internal-LED":
        return "UL 48 sign + UL 879/879A components"
    if illumination == "neon":
        return "UL 48 neon sign"
    return None


