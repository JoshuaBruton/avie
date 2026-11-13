# A.V.I.E.

**Anomaly Vision Intelligence Engine** retrieves or imports geospatial imagery,
runs YOLOv8 detection on eligible aerial captures, and saves scan reports.
The default location is Stonehenge (51.1789, -1.8262).

## Imagery requirements

- Detailed baseline: verified **native capture GSD ≤5 cm/pixel**, preferably 2–3 cm.
  Resampling, AI sharpening, map zoom and output pixel size do not establish GSD.
- Capture age is unrestricted. Historical imagery is acceptable.
- A provider/licence reference and explicit permission for analysis and app display
  are required. These fields record verified rights; changing a flag does not grant rights.
- People and medium-animal detection remain experimental: qualifying resolution
  is an input requirement, not a guarantee of model accuracy. Validate against
  manually labelled overhead imagery before trusting counts or alerts.
- Recent satellite/context imagery is a separate layer and cannot establish
  present-day people or animal observations from historical aerial imagery.

## Run a scan

Install requirements with `pip install -r requirements.txt`.
Copy `data/metadata/stonehenge.example.json` and fill in confirmed provider metadata.
The example deliberately fails eligibility until coverage and rights are verified.

```sh
python scripts/main.py --image /path/to/licensed-stonehenge-image.tif --metadata /path/to/metadata.json
```

Use a georeferenced provider export/crop covering the selected coordinates. The
current importer processes the supplied image; it does not crop a regional mosaic
or infer coordinates from it. Use `--lat` and `--lon` for another location.

Metadata fields:

- `native_gsd_cm`: positive numeric native capture GSD in centimeters.
- `source_type`: `aerial`; `source`: provider/survey identifier.
- `license_reference`: agreement permitting the intended use.
- `analysis_permitted`, `display_permitted`: true only after rights are verified.
- `captured_at`: ISO timestamp with timezone, if known, e.g. `2020-06-01T10:30:00Z`.
- Otherwise `capture_date`: `YYYY-MM-DD`, or `capture_date_range`:
  `{"start": "2020-01-01", "end": "2020-12-31"}`.

No-argument mode optionally downloads a Google Static Maps **context** image using
`GOOGLE_API_KEY` from the environment. Native resolution, capture date and usage
rights are unverified for that image, so detailed detection is skipped and a
limitation report is saved. The download timestamp is never treated as capture time.
No provider has been purchased, selected or integrated for high-detail Stonehenge
coverage. Check Bluesky/Woolpert and Getmapping archives, including older captures;
request a native-resolution sample, date metadata and app/AI licence before choosing.

## Reports and viewer

Reports append to `logs/detections.jsonl` and include source metadata, native GSD,
capture date/time (or supplied range/unavailable), separate UTC analysis timestamp,
limitations, detection status, and findings tied to the captured image.
A blocked scan is `not_run_insufficient_imagery`, never a successful zero-detection
scan. Existing reports retain their original analysis timestamps and are shown
with unverified imagery status; no historical capture dates are invented.

Run `python scripts/tile_viewer.py` to inspect reports (requires Tk and
`ttkbootstrap`). Images fit within 480×480 pixels without enlargement or distortion.
The viewer shows “High-detail imagery unavailable for this location” when required
metadata is missing. No synthetic enhancement is applied.

Run policy/report checks with `python -m unittest discover -s tests -v`.

## Current interactive application

The current dark satellite-analysis GUI, persistent scan API, and Python worker are in **[app/](app/README.md)**. The original CLI scripts remain available.

The app includes overlapping-tile satellite analysis, structure/remnant candidates, dedicated aerial human detection, wildlife categories, mapped agriculture and heritage context, saved reviews/history, close-up rescans, and reviewed training-crop export. Image candidates are unconfirmed; known map records are labelled separately. No detector identifies every person or archaeological site.

See [app/README.md](app/README.md) for setup, licensing, and limitations, and [app/VALIDATION.md](app/VALIDATION.md) for verification evidence. Custom human training needs reviewed positive/negative examples and independent-site validation; it does not run automatically. Credentials and downloaded model weights are excluded.

Native-resolution eligibility and capture-metadata reporting are integrated into both the CLI and the web app. The web app supports private licensed aerial imports and a separate context layer; see app/README.md for the external worker v7 upgrade. Qualifying Stonehenge provider coverage remains unverified.
