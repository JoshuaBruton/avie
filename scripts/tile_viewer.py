import os
import json
from PIL import Image, ImageTk
import tkinter as tk
from ttkbootstrap import Style
from ttkbootstrap.constants import *

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from brutils.paths import DETECTIONS_LOG, ANNOTATED_OUTPUT
from brutils.imagery import assess_imagery, capture_label


class TileViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("A.V.I.E. Tile Viewer")
        self.style = Style("cyborg")  # Dark theme

        self.index = 0
        self.entries = self.load_logs()

        self.img_label = tk.Label(self.root)
        self.img_label.pack(padx=10, pady=10)

        self.meta_text = tk.Text(self.root, height=10, wrap="word")
        self.meta_text.pack(padx=10, pady=5, fill="x")

        nav_frame = tk.Frame(self.root)
        nav_frame.pack(pady=5)

        self.prev_btn = tk.Button(nav_frame, text="⟵ Prev", command=self.prev_tile)
        self.prev_btn.pack(side="left", padx=5)

        self.next_btn = tk.Button(nav_frame, text="Next ⟶", command=self.next_tile)
        self.next_btn.pack(side="right", padx=5)

        self.display_tile()

    def load_logs(self):
        if not os.path.exists(DETECTIONS_LOG):
            print("No detection logs found.")
            return []

        with open(DETECTIONS_LOG, "r") as f:
            return [json.loads(line) for line in f]

    def display_tile(self):
        if not self.entries:
            self.meta_text.insert("1.0", "No entries to display.")
            return

        entry = self.entries[self.index]
        raw_img_path = entry.get("image_path", "")
        base_filename = os.path.basename(raw_img_path)
        annotated_img_path = os.path.join(ANNOTATED_OUTPUT, base_filename)

        eligible = assess_imagery(entry.get("imagery", {}))["eligible"]
        image_path = annotated_img_path if eligible and os.path.exists(annotated_img_path) else raw_img_path

        if os.path.exists(image_path):
            img = Image.open(image_path)
            img.thumbnail((480, 480))  # Never enlarge beyond source pixels.
            photo = ImageTk.PhotoImage(img)
            self.img_label.config(image=photo)
            self.img_label.image = photo
        else:
            self.img_label.config(text="Image not found.")

        # Show metadata
        self.meta_text.delete("1.0", tk.END)
        info = f"""
Image captured: {capture_label(entry.get('imagery', {}))}
Analysis performed: {entry.get('analysis_at', entry.get('timestamp', 'Unavailable'))}
Source: {entry.get('imagery', {}).get('source', 'Unverified')}
Native resolution: {entry.get('imagery', {}).get('native_gsd_cm') or 'Unknown'} cm/pixel
Status: {entry.get('detection_status', 'Legacy report: imagery suitability unverified')}
Findings describe the captured image, not current conditions.
📍 Coordinates: {entry['coordinates']['latitude']}, {entry['coordinates']['longitude']}

🎯 Detections:
"""
        assessment = assess_imagery(entry.get("imagery", {}))
        if not assessment["eligible"]:
            info += "High-detail imagery unavailable for this location.\n"
            info += "\n".join(assessment["limitations"]) + "\n"
        for det in (entry.get("detections", []) if assessment["eligible"] else []):
            info += f"   - {det['class_name']} ({det['confidence']:.2f})\n"

        filters = entry.get("filters", {})
        info += "\n🔎 Filters:\n"
        for f, enabled in filters.items():
            info += f"   - {f}: {'✅' if enabled else '❌'}\n"

        self.meta_text.insert("1.0", info.strip())

    def next_tile(self):
        if self.index < len(self.entries) - 1:
            self.index += 1
            self.display_tile()

    def prev_tile(self):
        if self.index > 0:
            self.index -= 1
            self.display_tile()


if __name__ == "__main__":
    root = tk.Tk()
    app = TileViewer(root)
    root.mainloop()
