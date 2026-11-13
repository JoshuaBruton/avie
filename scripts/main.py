"""Scan a licensed aerial baseline, or report limitations on a context image."""
import argparse
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from brutils.config import CENTER_LAT, CENTER_LON
from brutils.paths import RAW_IMAGE_DIR
from brutils.formatting import format_filename
from brutils.imagery import assess_imagery
from scripts.flag_anomalies import log_detections


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", help="Local licensed aerial image (not resampled to claim finer resolution)")
    parser.add_argument("--metadata", help="JSON metadata for this image; required with --image")
    parser.add_argument("--lat", type=float, default=CENTER_LAT)
    parser.add_argument("--lon", type=float, default=CENTER_LON)
    args = parser.parse_args()
    if bool(args.image) != bool(args.metadata):
        parser.error("Supply --image and --metadata together.")
    lat, lon = args.lat, args.lon
    if args.image:
        if not os.path.isfile(args.image):
            parser.error("Image file does not exist.")
        with open(args.metadata) as stream:
            metadata = json.load(stream)
        if not isinstance(metadata, dict):
            parser.error("Metadata must be a JSON object.")
        final_path = os.path.abspath(args.image)
    else:
        from scripts.download_image import download_satellite_image
        final_path = os.path.join(RAW_IMAGE_DIR, format_filename(lat, lon))
        if not download_satellite_image(lat, lon, save_path=final_path):
            return
        metadata = {"source": "Google Static Maps", "source_type": "context",
                    "native_gsd_cm": None}
    assessment = assess_imagery(metadata)
    results = []
    if assessment["eligible"]:
        from scripts.detect import run_detection
        results = run_detection(final_path, imagery_metadata=metadata)
    else:
        print("High-detail imagery unavailable for this location.")
        for reason in assessment["limitations"]:
            print(f"- {reason}")
    log_detections(results, lat, lon, final_path, imagery_metadata=metadata)


if __name__ == "__main__":
    main()
