# A.V.I.E. — Anomaly Vision Intelligence Engine

**A.V.I.E.** is an ongoing geospatial computer-vision project for exploring, reviewing, and documenting potential features in aerial imagery. It combines a browser-based analysis and review application with a persistent scan API, a separately hosted Python inference worker, and an original command-line workflow.

The project brings together computer vision, geospatial processing, imagery provenance, map-based context, and human-in-the-loop review. It is designed to help an analyst investigate candidate features, not to make unsupported claims about what an image proves.

> **Project status:** Ongoing project. The core application, scan/review workflows, imagery policy, and inference pipeline are implemented and continue to evolve. Detection models and some target categories remain experimental and require further independent validation.

---

## What A.V.I.E. does

A.V.I.E. supports two distinct imagery workflows:

- **Detailed aerial analysis:** Imports a licensed, georeferenced aerial image with verified capture and licensing metadata. Eligible imagery can be processed by the inference pipeline.
- **Context and map evidence:** Provides satellite/map context and separately sourced geographic information. Context imagery is not treated as a substitute for verified high-resolution aerial data, and it does not run detailed image detection under the current imagery policy.

The application supports investigation of:

- Buildings, roofs, and other structure candidates
- Archaeological or historic-structure-remnant candidates
- People and possible human-presence candidates
- Wildlife and animal candidates
- Road transport, trains, and boats
- Unknown visual-feature proposals
- Mapped agriculture and heritage information
- Manually marked observations and analyst assessments

These categories do not all use the same evidence source or detection method. Model-generated candidates, geometry-based proposals, mapped records, and manual annotations are kept distinguishable for review.

## Application capabilities

### Browser dashboard and scan management

The private web application in [app/](app/) includes:

- A dark, map-oriented analysis interface
- Scan creation, status monitoring, and engine-health reporting
- Target-group, model, tile-size, radius, and confidence settings
- Persistent scan history and report retrieval
- Saved reviews, annotations, labels, and analyst notes
- Manual feature marking and assessment
- Linked close-up investigations and rescans
- JSON report export and reviewed-example library workflows

### Image analysis and geospatial processing

For eligible aerial imports, the Python pipeline supports:

- Overlapping image tiles and inference
- Detection deduplication and radius filtering
- Image-based coordinate estimation
- Building-footprint segmentation suggestions
- Dedicated aerial human-candidate detection
- Experimental wildlife localization and candidate review
- Exploratory structure/remnant proposals
- Annotated imagery and analysis charts

A scan's findings are tied to the source imagery and its capture metadata. Coordinates are estimates derived from image geometry, not surveyed positions.

### Geographic context and location inspection

The application can supplement image review with separately identified geographic sources:

- OpenStreetMap place-name resolution and mapped features
- Mapped agriculture and known heritage records
- OpenStreetMap links for scan areas and findings
- Panoramax nearby street-level photo availability checks
- Google Street View and Mapillary coverage-check links

Mapped features are context, not image discoveries. A nearby street-level photo does not prove that a candidate is visible from that camera position.

### Human review and training-data preparation

Analysts can mark features, add labels and notes, save assessments, and create reviewed image crops. The private example library supports review, deletion, and ZIP export.

Reviewed examples are **not automatically used to train or update a model**. A separate preparation workflow applies minimum sample and geographic-separation safeguards before a custom human-model training candidate can be prepared. Any candidate model still requires suitable data rights and independent geographic validation before it could be considered for use.

---

## Imagery integrity and analysis policy

Imagery quality and usage rights are central to A.V.I.E.'s design. A detailed detection result is only meaningful when the underlying source is suitable and its provenance is understood.

### Requirements for detailed aerial analysis

The current imagery policy (v7) requires:

- Verified native aerial ground sample distance (GSD) of **5 cm/pixel or better**, preferably 2–3 cm/pixel
- Delivered image pixel spacing of **5 cm/pixel or better**
- Provider/source identification and a licence reference
- Confirmed permission for both AI analysis and display in the application
- Georeferencing and coverage metadata sufficient to locate the imported image and contain the requested scan area

The image must preserve genuine source detail. Resampling, enlargement, digital zoom, AI sharpening, or a map zoom level cannot be used to claim better native resolution. Imported images are limited to 4096 pixels per side and 8 MB per input image. The entire requested scan circle must fit within the imported image footprint.

Capture age is not restricted. Historical aerial imagery can be used when its provenance, resolution, and usage rights meet the requirements.

### Context imagery is not detailed evidence

Esri World Imagery is currently used as a separate context layer. Its native capture resolution, exact capture date, and detailed-analysis rights are not verified by the application. Therefore:

- Context imagery does not run detailed image detectors under the current v7 policy.
- A context-only scan reports `not_run_insufficient_imagery`, not a successful scan with zero detections.
- Mapped records and manual observations remain separately identified.
- A download or import timestamp is never substituted for the image's capture date.

The original CLI can optionally retrieve a Google Static Maps context image using `GOOGLE_API_KEY`. That image is also treated as context, not as an eligible high-detail aerial baseline.

### Capture metadata and reporting

Scan reports preserve the precision of supplied capture information, including date-only and date-range values. They distinguish:

- Source/provider and licence reference
- Native capture GSD and delivered pixel spacing
- Capture date/time, when known
- UTC analysis timestamp
- Detection status, findings, and limitations

Unknown capture information remains explicitly unavailable. Reports refer to the imagery's capture period, not necessarily present-day conditions. Older reports with unverified imagery metadata remain historical records and are labelled accordingly.

**Current coverage note:** No qualifying high-detail Stonehenge baseline has been purchased or verified. Provider candidates mentioned in the application documentation are research leads, not integrated or approved imagery sources.

---

## Models, evidence types, and limitations

A.V.I.E. combines third-party models and exploratory algorithms. The current implementation is not a universal anomaly detector, archaeological classifier, wildlife survey system, or people-counting system.

| Capability | Current approach | Important qualification |
|---|---|---|
| General object detection | Ultralytics YOLOv8 COCO models | General-purpose weights, not specialized satellite models |
| Buildings and roofs | Separate YOLOv8 building-footprint segmentation model | Suggests outlines; does not determine a structure's purpose |
| Aerial human candidates | Third-party YOLOv8s-VisDrone model | Experimental on A.V.I.E. imagery; not identification, tracking, or a census |
| Wildlife localization | General animal classes with optional OWL-C aerial localization | Experimental; localization is not species confirmation or calibrated confidence |
| Archaeology / remnants | Multiscale contrast and stone-shadow cluster proposals | Exploratory geometry proposals, not a trained archaeological classifier |
| Unknown visual features | Bounded geometry-based proposals | No classification probability; natural features can be proposed |
| Agriculture and known heritage | OpenStreetMap data | Mapped context, not image-based crop or archaeological discovery |
| Manual observations | Analyst-drawn regions, labels, notes, and assessments | Human review remains distinct from model output |

Some categories, including marine and reptilian wildlife, currently support manual marking and review rather than specialist automatic classification. The Living Organisms workflow does not detect every kind of living thing.

### Accuracy and interpretation

- A candidate is not a confirmed finding.
- A model score or localization value is not automatically a calibrated probability.
- A possible-person box is not proof of a person's presence, identity, or current location.
- A wildlife candidate does not establish species or population.
- A structure proposal does not establish human origin, age, or archaeological significance.
- Mapped features may be incomplete, generalized, or outdated.
- Small objects, vegetation, shadows, image quality, and capture resolution can affect results.
- **Zero detections never establishes that an area is empty.**

Independent-site precision/recall and complete survey performance have not been established for the people or wildlife workflows. No custom A.V.I.E. human model has been trained or activated from the reviewed-example library.

### Third-party model licensing

Model code and model weights can have different licences. In particular, the optional OWL-C implementation includes weights distributed under **CC BY-NC-SA 4.0**, which has non-commercial and share-alike conditions. The dedicated VisDrone human model and its training data also have their own terms. Review the applicable model cards, dataset terms, and software licences before commercial use, redistribution, or training.

See [app/README.md](app/README.md) for model references, attribution, and the more detailed technical limitations.

---

## Architecture

The current application is split into a browser/API layer and a separately hosted Python inference service.

| Component | Responsibility |
|---|---|
| `app/public/` | Browser interface and client-side application |
| `app/worker/index.js` | Authenticated application API, persistent job queue, scan status, history, reviews, and report downloads |
| Cloudflare R2 (`BUCKET`) | Persistent scan records, source imagery, annotated images, and plots |
| `app/backend/worker.py` | Outbound Python worker that claims and processes scan jobs |
| `app/backend/pipeline.py` | Image preparation, tiling, inference, geospatial filtering, annotations, and charts |
| `app/backend/` | Detection helpers, model integrations, tests, and reviewed-example training preparation |
| `scripts/`, `brutils/` | Original command-line scanner, imagery utilities, reporting, and desktop viewer |

The Python worker communicates outbound to the application API; it does not require a publicly exposed Python service port or tunnel. The private site uses Sites authentication. The worker authenticates with a Site service-access token and a separate `AVIE_WORKER_TOKEN`. Credentials, private imagery, scan history, and downloaded model weights must stay out of source control and browser code.

The web application and Python worker are deployed separately. Publishing the browser/API layer does not automatically update or restart the Python worker.

---

## Getting started

A.V.I.E. currently has two entry points: the original Python CLI and the newer browser application with its external worker.

### 1. Original Python CLI

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Run a scan against a licensed aerial image and its metadata JSON:

```bash
python scripts/main.py \
  --image /path/to/licensed-aerial-image.tif \
  --metadata /path/to/metadata.json
```

The metadata template is [data/metadata/stonehenge.example.json](data/metadata/stonehenge.example.json). Its placeholder values are intentionally insufficient for detailed analysis until replaced with verified provider, resolution, capture, and licence information.

Use `--lat` and `--lon` to specify another scan center. The requested coordinates must be covered by the supplied image. If no image/metadata pair is provided, the CLI can optionally download a Google Static Maps context image using `GOOGLE_API_KEY`; detailed detection is skipped when the imagery eligibility requirements are not met.

To inspect saved reports with the original desktop viewer:

```bash
python scripts/tile_viewer.py
```

The viewer uses Tkinter and `ttkbootstrap`. CLI reports append to `logs/detections.jsonl`.

### 2. Browser application and Python worker

The current web application lives in [app/](app/). Its setup, imagery-import workflow, worker deployment, configuration, and operational details are documented in [app/README.md](app/README.md).

At a high level:

1. Build and publish the private browser/API application using the existing Sites configuration.
2. Run the Python worker on a persistent host or container with its required secrets.
3. Keep the worker's model cache on persistent storage.
4. Confirm the worker heartbeat and analysis version through the authenticated health endpoint before submitting detailed aerial jobs.

The worker requires `AVIE_SITE_URL`, `AVIE_SITE_SERVICE_TOKEN`, and `AVIE_WORKER_TOKEN`. Variable names are documented in [app/.env.example](app/.env.example); that file is a reference, not an automatically loaded secrets file. Configure actual values through the hosting platform's secret manager. Never commit real credentials.

For the exact Python dependencies, Docker build command, worker-version requirements, and application workflow, follow [app/README.md](app/README.md). The current aerial-import policy requires worker analysis version 7 or newer.

---

## Development and verification

### Web application

Run these commands from `app/`:

```bash
node build.mjs
node --test tests/*.test.mjs
PYTHONPATH=backend python -m unittest discover -s backend -p 'test_*.py'
```

Build before running the Node tests because API tests import the generated `dist/server/index.js`. Python checks require the backend dependencies from `app/backend/requirements.txt`.

### Original CLI

Run from the repository root:

```bash
python -m unittest discover -s tests -v
```

The latest documented verification record is in [app/VALIDATION.md](app/VALIDATION.md). It records the results of the November 13, 2026 checks: 20 web/API tests, 24 Python backend tests, and 5 original CLI tests passed in the managed development environment. These software checks do not establish field accuracy or model precision/recall. The validation document also distinguishes repository checks, historical experiments, and live deployment status.

---

## Repository layout

```text
avie/
├── app/
│   ├── backend/          # Python inference pipeline and worker
│   ├── public/           # Browser application
│   ├── worker/           # Application API and persistent job handling
│   ├── tests/            # Web/API and imagery-policy tests
│   ├── README.md         # Detailed web app and worker documentation
│   └── VALIDATION.md     # Verification, limitations, and deployment status
├── brutils/              # Shared CLI utilities
├── data/
│   └── metadata/         # Example imagery metadata
├── logs/                 # Local CLI scan reports
├── scripts/              # Original CLI, detection, and viewer scripts
├── tests/                # Original CLI tests
├── requirements.txt      # Original CLI dependencies
└── README.md
```

---

## Project direction

A.V.I.E. is an ongoing research and engineering project. Current work is centered on improving the quality and provenance of usable imagery, strengthening human-review workflows, expanding and validating specialized detection approaches, and keeping model-generated findings separate from geographic context and manual observations.

Potential future work includes independently validated overhead-imagery models, broader geographic and species/site evaluation, additional imagery sources with suitable licensing, and carefully validated custom models. These are development directions, not claims that those capabilities are already complete.

## Licence and responsible use

Review the repository's licence and each third-party model, dataset, and imagery provider's terms before using or redistributing code, weights, data, or results. Imagery rights for AI analysis, application display, and model training are separate considerations. A.V.I.E. does not grant rights to imagery or third-party model assets.

A.V.I.E. is an exploratory analysis and human-review tool. It should not be used as the sole basis for law-enforcement action, identification or tracking of people, wildlife population claims, archaeological conclusions, or other high-impact decisions.

---

**Repository:** [github.com/JoshuaBruton/avie](https://github.com/JoshuaBruton/avie)  
**Detailed application documentation:** [app/README.md](app/README.md)  
**Validation and deployment notes:** [app/VALIDATION.md](app/VALIDATION.md)
