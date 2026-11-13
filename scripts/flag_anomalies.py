# scripts/flag_anomalies.py

import os
import json
from datetime import datetime, timezone

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from brutils.paths import DETECTIONS_LOG
from brutils.imagery import assess_imagery, capture_label

def log_detections(results, lat, lon, image_path, selected_filters=None, output_path=DETECTIONS_LOG,
                   imagery_metadata=None):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    imagery_metadata = imagery_metadata or {}
    assessment = assess_imagery(imagery_metadata)
    analysis_at = datetime.now(timezone.utc).isoformat()

    detections = []
    for result in (results if assessment["eligible"] else []):
        for box in result.boxes:
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            class_name = result.names.get(cls_id, "unknown")

            detections.append({
                "class_id": cls_id,
                "class_name": class_name,
                "confidence": confidence
            })

    log_entry = {
        "timestamp": analysis_at,
        "analysis_at": analysis_at,
        "imagery": imagery_metadata,
        "capture_label": capture_label(imagery_metadata),
        "imagery_assessment": assessment,
        "detection_status": "completed" if assessment["eligible"] else "not_run_insufficient_imagery",
        "findings_context": "Findings describe the captured image, not current conditions.",
        "coordinates": {
            "latitude": lat,
            "longitude": lon
        },
        "image_path": image_path,
        "detections": detections,
        "filters": selected_filters or {}
    }

    with open(output_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"Report saved to {output_path} ({log_entry["detection_status"]})")
    return log_entry
