"""Source metadata and eligibility rules; image age is intentionally unrestricted."""
import math
from datetime import date, datetime

MAX_GSD_CM = 5
PREFERRED_GSD_CM = 3


def assess_imagery(metadata):
    """Require declared native capture resolution and explicit permitted uses."""
    gsd = metadata.get("native_gsd_cm")
    valid_gsd = (isinstance(gsd, (int, float)) and not isinstance(gsd, bool)
                 and math.isfinite(gsd) and 0 < gsd <= MAX_GSD_CM)
    reasons = []
    if not valid_gsd:
        reasons.append("Native resolution must be verified at 5 cm/pixel or better.")
    if metadata.get("source_type") != "aerial":
        reasons.append("A verified aerial baseline is required for detailed detection.")
    if not metadata.get("source"):
        reasons.append("Imagery source is unverified.")
    if not metadata.get("license_reference"):
        reasons.append("Imagery licence reference is missing.")
    for permission in ("analysis_permitted", "display_permitted"):
        if metadata.get(permission) is not True:
            reasons.append(f"{permission.replace('_', ' ').capitalize()} is unverified.")
    return {
        "eligible": not reasons,
        "status": "eligible" if not reasons else "unavailable",
        "preferred_resolution": valid_gsd and gsd <= PREFERRED_GSD_CM,
        "limitations": reasons,
        "requirement": "Native aerial imagery at 5 cm/pixel or better; preferably 2–3 cm.",
    }


def capture_label(metadata):
    """Preserve supplied precision; never substitute download/analysis time."""
    captured = metadata.get("captured_at")
    if captured:
        try:
            parsed = datetime.fromisoformat(captured.replace("Z", "+00:00"))
            if "T" in captured and parsed.tzinfo is not None:
                return captured
        except (ValueError, TypeError, AttributeError):
            pass
    captured_date = metadata.get("capture_date")
    if captured_date:
        try:
            date.fromisoformat(captured_date)
            return f"{captured_date} (capture time unavailable)"
        except (ValueError, TypeError):
            pass
    period = metadata.get("capture_date_range")
    if isinstance(period, dict):
        try:
            start, end = date.fromisoformat(period["start"]), date.fromisoformat(period["end"])
            if start <= end:
                return f"{start} to {end} (exact capture date/time unavailable)"
        except (ValueError, TypeError, KeyError):
            pass
    return "Capture date/time unavailable"
