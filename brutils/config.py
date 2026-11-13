import os

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
CENTER_LAT = 51.1789
CENTER_LON = -1.8262
RADIUS_MILES = 5
ZOOM_LEVEL = 17  # 0 (farthest) to 21+ (closest)
IMAGE_SIZE = "640x640"  # Max size for free-tier: 640x640
