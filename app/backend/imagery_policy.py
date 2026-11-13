"""Detailed aerial eligibility; capture age is unrestricted."""
import base64
import io
import math
from datetime import date, datetime
from PIL import Image


def assess_imagery(info):
    n = info.get('nativeGsdCm')
    valid = isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n) and 0 < n <= 5
    limitations = []
    if not valid:
        limitations.append('Native capture resolution must be verified at 5 cm/pixel or better.')
    if info.get('sourceType') != 'aerial':
        limitations.append('A verified aerial baseline is required for detailed detection.')
    if not info.get('provider') or not info.get('licenseReference'):
        limitations.append('Imagery source and licence reference must be verified.')
    if info.get('analysisPermitted') is not True or info.get('displayPermitted') is not True:
        limitations.append('AI analysis and app display permissions must be verified.')
    spacing = info.get('groundResolutionMeters')
    if not isinstance(spacing, (int, float)) or isinstance(spacing, bool) or not math.isfinite(spacing) or not 0 < spacing <= .050001:
        limitations.append('Delivered image pixel spacing must be 5 cm or better.')
    return {'eligible': not limitations, 'status': 'unavailable' if limitations else 'eligible',
            'preferredResolution': valid and n <= 3, 'limitations': limitations,
            'requirement': {'maxNativeGsdCm': 5, 'preferredNativeGsdCm': [2, 3], 'freshnessRequired': False}}


def capture_label(info):
    timestamp = info.get('capturedAt')
    if isinstance(timestamp, str) and 'T' in timestamp:
        try:
            if datetime.fromisoformat(timestamp.replace('Z', '+00:00')).tzinfo:
                return timestamp
        except ValueError:
            pass
    try:
        return f"{date.fromisoformat(info['captureDate'])} (capture time unavailable)"
    except (KeyError, ValueError, TypeError):
        pass
    try:
        period = info['captureDateRange']
        start, end = date.fromisoformat(period['start']), date.fromisoformat(period['end'])
        if start <= end:
            return f'{start} to {end} (exact capture date/time unavailable)'
    except (KeyError, ValueError, TypeError):
        pass
    return 'Capture date/time unavailable'


def load_baseline(baseline):
    """Decode uploaded pixels without resizing to satisfy a claimed GSD."""
    info = dict(baseline['imagery'])
    if not assess_imagery(info)['eligible']:
        raise ValueError('Imported baseline does not meet the imagery requirements.')
    raw = base64.b64decode(baseline['imageBase64'], validate=True)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('Baseline exceeds 8 MB.')
    with Image.open(io.BytesIO(raw)) as original:
        if original.format not in ('JPEG', 'PNG') or original.size != (info['width'], info['height']):
            raise ValueError('Image dimensions do not match metadata, or format is unsupported.')
        if max(original.size) > 4096:
            raise ValueError('Baseline exceeds 4096 native pixels per side.')
        image = original.convert('RGB')
    return image, info
