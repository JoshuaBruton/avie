# A.V.I.E. — Anomaly Vision Intelligence Engine

**A.V.I.E.** is an ongoing geospatial computer-vision project for exploring, reviewing, and documenting potential features in aerial imagery.

The project brings together a browser-based analysis application, a persistent scan and review API, a separately hosted Python inference worker, and the original Python command-line workflow. Its focus is not simply detecting objects. It is building a traceable analysis environment where imagery provenance, geographic context, model-generated candidates, and human observations remain distinguishable.

A.V.I.E. is designed to support investigation, not to turn uncertain image detections into unsupported conclusions.

> **Project status:** Ongoing project. The core application, scan and review workflows, imagery eligibility controls, and inference pipeline are implemented and continue to evolve. Some detection categories remain experimental and require independent validation.

---

## At a glance

- **Two workflows:** Original Python CLI and browser-based analysis application.
- **Computer vision:** Object detection, building-footprint suggestions, aerial human candidates, and experimental wildlife localization.
- **Geospatial processing:** Image tiling, coordinate estimation, radius filtering, mapped context, and location inspection.
- **Human review:** Manual feature marking, labels, notes, saved assessments, and reviewed-example exports.
- **Persistent records:** Scan history, reports, imagery, annotations, and review data stored through the application backend and R2.
- **Evidence-aware reporting:** Source imagery, capture metadata, analysis timestamps, evidence types, and limitations are kept explicit.

## What A.V.I.E. does

A.V.I.E. supports two different imagery workflows. They are intentionally not interchangeable.

### Detailed aerial analysis

Eligible, licensed aerial imagery can be imported with its source metadata and processed by the Python inference pipeline. This is the workflow used for detailed image-based detection.

The current imagery policy requires:

- Verified native aerial ground sample distance (GSD) of **5 cm/pixel or better**, preferably 2–3 cm/pixel.
- Delivered pixel spacing of 5 cm/pixel or better.
- Identified imagery provider/source and a licence reference.
- Confirmed permission for both AI analysis and display in the application.
- Georeferencing and coverage metadata sufficient to contain the requested scan area.

The imported image must preserve genuine source detail. Enlarging, resampling, digitally zooming, or sharpening an image does not qualify it for a higher native resolution. Imported images are limited to 4096 pixels per side and 8 MB per image. The full requested scan circle must fit within the image footprint.

Historical imagery is acceptable when its provenance, resolution, and usage rights meet the requirements. Capture age is not itself a restriction.

### Geographic context

A.V.I.E. can also use separately identified map and geographic sources to help an analyst understand an area.

The current Esri World Imagery layer is a **context layer**, not an eligible high-detail aerial baseline. Its native capture resolution, exact capture date, and detailed-analysis rights are not verified by the application. Consequently, context-only scans do not run detailed image detectors. They report `not_run_insufficient_imagery`, rather than presenting an unsupported zero-detection result.

Mapped records and manual observations are retained as separate evidence types. They are not counted as image discoveries.

## Application capabilities

### Browser dashboard and scan management

The browser application in [app/](app/) provides:

- Map-oriented analysis interface and scan configuration.
- Scan creation, progress, status, and engine-health reporting.
- Target-group, model, tile-size, radius, and confidence settings.
- Persistent scan history and report retrieval.
- Saved reviews, annotations, labels, and analyst notes.
- Manual feature marking and assessment.
- Linked close-up investigations and rescans.
- JSON report exports and reviewed-example library workflows.

### Image analysis and geospatial processing

For eligible aerial imports, the Python pipeline supports:

- Overlapping image tiles and model inference.
- Detection deduplication and geographic radius filtering.
- Image-based coordinate estimation.
- Building-footprint segmentation suggestions.
- Dedicated aerial human-candidate detection.
- Experimental wildlife localization and candidate review.
- Exploratory structure/remnant proposals.
- Annotated imagery and analysis charts.

Coordinates are estimated from image geometry. They are not surveyed positions.

### Geographic context and location inspection

The application can supplement image review with separately identified geographic information:

- OpenStreetMap place-name resolution and mapped features.
- Mapped agriculture and known heritage records.
- OpenStreetMap links for scan areas and findings.
- Panoramax nearby street-level photo availability checks.
- Google Street View and Mapillary coverage-check links.

Mapped information is contextual evidence, not an image-based discovery. The availability of a nearby street-level photograph does not establish that a particular feature is visible from that camera position.

### Human review and example preparation

Analysts can mark features, assign labels, add notes, save assessments, and create reviewed image crops.

The private example library supports review, deletion, and ZIP export. Reviewed examples are **not automatically used to train or update a model**.

A separate preparation workflow applies minimum sample-count and geographic-separation safeguards before a custom human-model training candidate can be prepared. Any candidate still requires appropriate data rights and independent geographic validation before it could be considered for deployment.

---

## Detection targets and current limitations

A.V.I.E. combines general-purpose third-party models, specialized third-party aerial models, exploratory algorithms, mapped records, and manual observations. These approaches have different evidentiary value.

| Target or capability | Current approach | Important qualification |
|---|---|---|
| General objects and transport | Ultralytics YOLOv8 COCO models | General-purpose weights, not specialized satellite models |
| Buildings and roofs | Separate YOLOv8 building-footprint segmentation model | Suggests outlines; does not determine a structure's purpose |
| Aerial human candidates | Third-party YOLOv8s-VisDrone model | Experimental; not identification, tracking, or a census |
| Wildlife localization | General animal classes with optional OWL-C aerial localization | Experimental; localization does not confirm species |
| Archaeology and structure remnants | Multiscale contrast and stone-shadow cluster proposals | Exploratory geometry proposals, not a trained archaeological classifier |
| Unknown visual features | Bounded geometry-based proposals | No classification probability; natural features can be proposed |
| Agriculture and known heritage | OpenStreetMap data | Mapped context, not image-based crop or archaeological discovery |
| Manual observations | Analyst-drawn regions, labels, notes, and assessments | Human review remains distinct from model output |

The Living Organisms workflow does not detect every kind of living thing. General land-animal and person detection is experimental on overhead imagery. Marine animals and reptiles currently support manual marking and review rather than specialist automatic classification.

### Interpreting results responsibly

- A candidate is not a confirmed finding.
- A model score or localization value is not automatically a calibrated probability.
- A possible-person box is not proof of identity, presence, or current location.
- A wildlife candidate does not establish species or population.
- A structure proposal does not establish human origin, age, or archaeological significance.
- Mapped features may be incomplete, generalized, or outdated.
- Vegetation, shadows, image quality, object size, and capture resolution can affect results.
- **Zero detections never establishes that an area is empty.**

Independent-site precision, recall, and complete survey performance have not been established for the experimental people or wildlife workflows. No custom A.V.I.E. human model has been trained or activated from the reviewed-example library.

### Third-party model licensing

Model code and model weights can have different licences. In particular, the optional OWL-C implementation includes weights distributed under **CC BY-NC-SA 4.0**, which carries non-commercial and share-alike conditions. The dedicated VisDrone human model and its training data also have their own terms.

Review the applicable model cards, dataset terms, software licences, and imagery rights before commercial use, redistribution, or training.

For model references, attribution, and detailed technical limitations, see [app/README.md](app/README.md).

---

## Architecture

A.V.I.E. separates the browser/API application from the Python inference service.

| Component | Responsibility |
|---|---|
| `app/public/` | Browser interface and client-side application |
| `app/worker/index.js` | Authenticated application API, persistent job queue, scan status, history, reviews, and report downloads |
| Cloudflare R2 (`BUCKET`) | Persistent scan records, source imagery, annotated images, and plots |
| `app/backend/worker.py` | Outbound Python worker that claims and processes scan jobs |
| `app/backend/pipeline.py` | Image preparation, tiling, inference, geospatial filtering, annotations, and charts |
| `app/backend/` | Detection helpers, model integrations, tests, and reviewed-example preparation |
| `scripts/`, `brutils/` | Original CLI scanner, imagery utilities, reporting, and desktop viewer |

### How the services work together

1. An authenticated user configures and submits a scan through the browser application.
2. The application API validates the request and stores the job and related records.
3. The external Python worker claims an available job through the authenticated API.
4. The worker processes eligible imagery and reports progress and results.
5. The application stores the completed scan data and makes its report and review workflow available to the user.

The Python worker communicates outbound to the application API. It does not require a publicly exposed Python service port or tunnel.

The private site uses Sites authentication. The worker authenticates with a Site service-access token and a separate `AVIE_WORKER_TOKEN`. Credentials, private imagery, scan history, and downloaded model weights must stay out of source control and browser code.

**Deployment is split:** publishing the browser/API application does not automatically update or restart the external Python worker. The worker must be deployed and checked separately.

---

## Getting started

A.V.I.E. has two entry points: the original Python CLI and the browser application with its external worker.

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

Run a scan using a licensed aerial image and its metadata JSON:

```bash
python scripts/main.py \
  --image /path/to/licensed-aerial-image.tif \
  --metadata /path/to/metadata.json
```

The metadata template is [data/metadata/stonehenge.example.json](data/metadata/stonehenge.example.json). Its placeholder values are intentionally insufficient for detailed analysis until replaced with verified provider, resolution, capture, and licence information.

Use `--lat` and `--lon` to specify another scan center. The requested coordinates must be covered by the supplied image.

If no image/metadata pair is provided, the CLI can optionally retrieve a Google Static Maps context image using `GOOGLE_API_KEY`. This is context imagery, not an eligible high-detail aerial baseline, so detailed detection is skipped when imagery requirements are not met.

To inspect saved reports with the original desktop viewer:

```bash
python scripts/tile_viewer.py
```

The viewer uses Tkinter and `ttkbootstrap`. CLI reports are appended to `logs/detections.jsonl`.

### 2. Browser application and Python worker

The current browser application and worker documentation live in [app/](app/). See [app/README.md](app/README.md) for the complete imagery-import workflow, configuration, worker deployment, and operational instructions.

At a high level:

1. Publish the private browser/API application using the existing Sites configuration.
2. Run the Python worker on a persistent host or container.
3. Configure the worker's required secrets through the hosting platform's secret manager.
4. Keep the worker's model cache on persistent storage.
5. Confirm the worker heartbeat and analysis version through the authenticated health endpoint before submitting detailed aerial jobs.

The worker requires:

- `AVIE_SITE_URL`
- `AVIE_SITE_SERVICE_TOKEN`
- `AVIE_WORKER_TOKEN`

Variable names are documented in [app/.env.example](app/.env.example). That file is a reference, not an automatically loaded secrets file. Configure actual values through the hosting platform's secret manager. Never commit real credentials.

The current aerial-import policy requires worker analysis version **7 or newer**. The exact Python dependencies, Docker build instructions, worker-version requirements, and application workflow are maintained in [app/README.md](app/README.md).

---

## Development and verification

### Browser application and API

Run these commands from `app/`:

```bash
node build.mjs
node --test tests/*.test.mjs
PYTHONPATH=backend python -m unittest discover -s backend -p 'test_*.py'
```

Build before running the Node tests because the API tests import the generated `dist/server/index.js`. Python checks require the backend dependencies from `app/backend/requirements.txt`.

### Original CLI

Run from the repository root:

```bash
python -m unittest discover -s tests -v
```

### Latest documented verification

The latest documented repository verification is recorded in [app/VALIDATION.md](app/VALIDATION.md). The November 13, 2026 validation record reports:

| Scope | Result |
|---|---:|
| Web/API tests | 20 passed |
| Python backend tests | 24 passed |
| Original CLI tests | 5 passed |

These checks cover application behavior, authentication, job handling, persistence, reviews, exports, imagery eligibility, worker compatibility, and other software workflows. They do **not** establish field accuracy, model precision/recall, or complete survey performance.

See [app/VALIDATION.md](app/VALIDATION.md) for the verification record, historical experiments, and deployment boundaries. Repository checks, frontend/API publication, and external worker deployment are separate operations.

---

## Repository structure

```text
avie/
├── app/
│   ├── backend/          # Python inference pipeline and worker
│   ├── public/           # Browser application
│   ├── worker/           # Application API and persistent job handling
│   ├── tests/            # Web/API and imagery-policy tests
│   ├── README.md         # Detailed application and worker documentation
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

A.V.I.E. is an ongoing research and engineering project. Current work is focused on:

- Improving the quality, provenance, and availability of eligible aerial imagery.
- Strengthening scan, review, annotation, and reporting workflows.
- Expanding and independently validating specialized detection approaches.
- Improving geographic context while preserving clear evidence-source boundaries.
- Building responsible workflows for reviewed examples and future custom models.
- Maintaining a reliable separation between the browser/API layer and the inference worker.

Potential future work includes independently validated overhead-imagery models, broader geographic and species/site evaluation, additional appropriately licensed imagery sources, and carefully validated custom models. These are research and engineering directions, not claims that those capabilities are already complete.

## Responsible use and licensing

Review the repository's licence and each third-party model, dataset, and imagery provider's terms before using or redistributing code, weights, data, or results. Rights for imagery analysis, application display, and model training are separate considerations. A.V.I.E. does not grant rights to imagery or third-party model assets.

A.V.I.E. is an exploratory analysis and human-review tool. It should not be used as the sole basis for law-enforcement action, identification or tracking of people, wildlife population claims, archaeological conclusions, or other high-impact decisions.

---

**Repository:** [github.com/JoshuaBruton/avie](https://github.com/JoshuaBruton/avie)  
**Application documentation:** [app/README.md](app/README.md)  
**Validation and deployment notes:** [app/VALIDATION.md](app/VALIDATION.md)
