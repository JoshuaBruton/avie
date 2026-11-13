# scripts/detect.py

import os
import matplotlib.pyplot as plt
from ultralytics import YOLO
from PIL import Image

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from brutils.paths import ANNOTATED_OUTPUT
from brutils.imagery import assess_imagery

def run_detection(image_path, model_path="yolov8n.pt", imagery_metadata=None):
    assessment = assess_imagery(imagery_metadata or {})
    if not assessment["eligible"]:
        raise ValueError("High-detail detection requires verified native aerial imagery and usage rights.")
    model = YOLO(model_path)

    results = model.predict(
        image_path,
        save=True,
        save_txt=True,
        project=os.path.dirname(ANNOTATED_OUTPUT),
        name="run"
    )

    result_img_path = os.path.join(ANNOTATED_OUTPUT, os.path.basename(image_path))

    if os.path.exists(result_img_path):
        img = Image.open(result_img_path)
        plt.imshow(img)
        plt.axis("off")
        plt.title("YOLOv8 Detection Results")
        plt.show()
    else:
        print("⚠️ Annotated result image not found.")

    return results
