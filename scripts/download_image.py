# scripts/download_image.py

import requests
import os
import sys
from io import BytesIO
from PIL import Image

# 🔥 Add parent dir (project root) to import path BEFORE other imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from brutils.config import ZOOM_LEVEL, IMAGE_SIZE, GOOGLE_API_KEY


def download_satellite_image(lat, lon, save_path="data/raw_images/sat_image.jpg"):
    """
    Downloads a satellite image from Google Static Maps API.
    """
    url = (
        f"https://maps.googleapis.com/maps/api/staticmap?"
        f"center={lat},{lon}&zoom={ZOOM_LEVEL}&size={IMAGE_SIZE}&maptype=satellite"
        f"&key={GOOGLE_API_KEY}"
    )

    if not GOOGLE_API_KEY:
        raise ValueError("Set GOOGLE_API_KEY for the optional context map download.")
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        img = Image.open(BytesIO(response.content)).convert("RGB")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        img.save(save_path)
        print(f"✅ Image saved to {save_path}")
        return save_path
    else:
        print(f"❌ Failed to fetch image! Status Code: {response.status_code}")

        return None


if __name__ == "__main__":
    lat, lon = 40.7128, -74.0060  # NYC
    download_satellite_image(lat, lon)
