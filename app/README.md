# AVIE — satellite analysis through the GUI

The original dark HTML/CSS/JS dashboard is now connected to real satellite acquisition and YOLOv8 inference. No simulated detections are generated.

## How to use

1. Open the private AVIE site and confirm **ENGINE ONLINE**.
2. Set decimal latitude/longitude, radius in kilometers, target object types, model, tile size, and confidence threshold.
3. Click **Initiate scan**. Acquisition, overlapping-tile inference, deduplication, and report progress come from the Python worker.
4. Click map annotations or detection rows to review findings. Reviews are saved server-side.
5. Export the JSON report, inspect the annotated imagery, or restore a scan from history.

Start with a 0.5 km radius and YOLOv8n. A 25% confidence threshold near an airport or harbor is useful for exploring candidates; every result still needs human analysis. The default 65% threshold is more selective.

## Architecture and persistence

- `public/`: browser interface, without secrets or Python dependencies.
- `worker/index.js`: authenticated Sites API, persistent job queue, status, history, reviews, and report downloads.
- Sites R2 binding `BUCKET`: scan records, source images, annotated images, and plots. Data is retained across deployments.
- `backend/pipeline.py`: imagery downloads, Pillow mosaics, OpenCV preparation/annotation, overlapping tiles, Ultralytics/PyTorch inference, torchvision class-aware NMS, geopy radius filtering, Web Mercator coordinate estimation, and matplotlib charts.
- `backend/worker.py`: outbound-only worker; no public Python port or tunnel is needed.

The site remains private using Sites authentication. The Python worker authenticates with both the Site service-access token and a separate `AVIE_WORKER_TOKEN` configured as a Site secret. Neither is shipped to the browser or committed to Git.

## Run the Python worker persistently

The chat workspace worker is for active development; it is not a permanent production host. New scans require a running worker. The GUI detects stale heartbeats and shows offline status, while completed reports remain available.

Use a persistent CPU host/container with at least 4 GB RAM for YOLOv8n; larger models need more resources. Install CPU PyTorch wheels first if appropriate for the host, then:

```
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
python backend/worker.py
```

Set `AVIE_SITE_URL`, `AVIE_SITE_SERVICE_TOKEN`, and `AVIE_WORKER_TOKEN` through the host's secret manager. See `.env.example` for names; it is documentation, not an automatically loaded file. The Site service token is obtained through the owner's Sites connection. `AVIE_WORKER_TOKEN` must match the secret configured on the Site. Do not place secret values in shell command history or source control.

For a container, build from the repository root with `backend/Dockerfile`, supply the same environment secrets at runtime, and mount a persistent `/models` volume. Standard YOLOv8n/s/m weights download from the official Ultralytics assets release on first use. The current development worker already has YOLOv8n cached.

## Imagery and model limits

Esri World Imagery needs no API key. Images are historical mosaics; the export endpoint does not supply capture dates, and this is not a live satellite feed. Provider attribution is shown in the interface and retained in reports. Follow the provider's terms for further use or distribution of imagery.

The mosaic is capped at 4096 × 4096 pixels. Larger radii therefore reduce effective ground resolution, which is reported for each scan. Tiles overlap by 20%; class-aware NMS removes duplicates before geodesic filtering to the requested radius. Antimeridian-crossing areas are rejected explicitly.

Standard YOLOv8 COCO weights are general-purpose, not specialized overhead detectors. Car, truck, boat, airplane, bus, and train are supported classes. Small objects can be missed or misclassified. Zero detections does not mean an area is empty. Coordinates are image-based estimates, not surveyed positions. Custom satellite-trained weights are a future improvement.

The repository's embedded Google API key is not copied or used. If Google Static Maps is added later, configure a fresh restricted key as a backend secret.

## Build and checks

```
node build.mjs
node --test tests/api.test.mjs
```

`build.mjs` bundles browser files with the ESM Worker into `dist/server/index.js`. `.openai/hosting.json` retains the original Sites project and declares R2. Python inference is hosted separately from the Sites Cloudflare Worker.

## Structure and unknown-feature analysis (v1.1)

The Building target runs a separate satellite-trained footprint segmentation model: `keremberke/yolov8n-building-segmentation` (Hugging Face). Its weights are cached separately as `buildings-yolov8n.pt`; the model can suggest building/roof outlines but cannot establish the purpose of a structure. Vehicle model selection remains independent.

Unknown visual features are bounded, geometry-based proposals for compact bright regions. They have **no classification probability** and can include rocks or other natural features. These are not a general anomaly detector, and dark, diffuse, or low-contrast features may be missed. A scan can include up to 750 model findings and 200 visual proposals. Class-aware NMS reduces duplicate model detections.

Use **Mark feature** to draw around any additional feature. The region, label, evidence source, estimated dimensions, notes, and assessment are saved with the scan and included in JSON exports. A manual mark stays unclassified; user assessments do not overwrite model probabilities. The report's **Export all current markings** includes manual annotations, while the original server-generated chart shows the original automatic results.

**Inspect location** and **Acquire close-up & rescan** create linked child scans with 50/100/250 m radii, retaining the parent overview in history. The API supports scan radii from 0.05 to 5 km; the form explicitly supports km and mi (conversion factor 1.609344). Digital zoom now reaches 32× and mouse-wheel zoom centers on the pointer. Enlarging pixels does not add information.

Detailed imagery requests probe supported provider scales. At places such as Göbekli Tepe, Esri may decline requests above level 18; the pipeline then reacquires at a supported scale and records `requestedZoom`, `samplingZoom`, `detailLimited`, and a report notice. This avoids presenting blank provider tiles or silently claiming higher native resolution. The acquired image's pixel spacing is reported; the source's native capture resolution and date remain unknown.

No model or setting finds or identifies everything. Satellite building suggestions, visual candidates, and manual observations must remain distinct evidence sources for human analysis.

## Grouped targets, wildlife, agriculture, and organisms (v1.3)

Section 02 now presents Road Transport (cars/trucks/buses), Train, Boat, Buildings/roofs, Unknown visual features, Wildlife/animals, Living Organisms, and Agriculture. Individual vehicle and aircraft checkboxes were removed. Old scan records remain readable; new close-ups normalize legacy road classes into Road Transport and omit aircraft.

Wildlife/animals is experimental. General COCO weights support Bird, Cat, Dog, Horse, Sheep, Cow, Elephant, Bear, Zebra, and Giraffe. The animal-class selection is saved and carried into close-ups. Living Organisms adds Person to those selected animal classes. It searches only supported people/animal classes, not all plants or living things. Selecting both groups does not run duplicate animal detections. A Person candidate does not identify an individual or establish a current location. These weights are not validated for satellite wildlife or human surveys.

The review pipeline retains species suggestions, probabilities, source, unknown/manual regions, labels, and notes. Possible animal, Possible organism, Possible person, and agricultural assessments can be saved without inventing a model classification. New JSON reports carry sampling context and experimental animal-mode metadata. Satellite imagery is historical; small bodies, canopy cover, and native resolution strongly limit useful detection. No detections does not establish absence of wildlife or people. For reliable wildlife surveys, use suitable high-resolution aerial/drone imagery and species-specific, validated models.

Agriculture uses bounded OpenStreetMap map extracts, with Overpass fallback, to mark mapped farmland, vineyards, orchards, farmyards, greenhouses, allotments, and meadow/grassland. Crop/produce tags such as grape, wheat, or corn are shown only where supplied by the map. **This is not image-based crop classification.** Geometry may be generalized or outdated and may differ from the satellite image. Mapped ways and multipolygon outer boundaries are supported; inner rings are retained for display. Extracts are bounded to 4 MB, four relation expansions, and 250 mapped features. Missing coverage, extraction limits, and unavailable providers are not evidence of no agriculture. Reports include data-source status, map tags, attribution, and `imageCropClassification: false`. Data attribution: © OpenStreetMap contributors, ODbL (https://www.openstreetmap.org/copyright).

Tests: `node build.mjs && node --test tests/api.test.mjs` and `PYTHONPATH=backend python -m unittest discover -s backend -p 'test_*.py'`.

## Place names and street-level inspection (v1.4)

A new scan resolves its center to a city/locality, state/region, and country through OpenStreetMap/Nominatim before it enters the vision queue. The location appears above the imagery and in the area metric, scan history, and JSON report. Missing address levels are omitted. Tibet is displayed as Tibet for the provider's Xizang/CN-XZ region; the original provider region/display name are retained in metadata. Labels describe the center, not every administrative area intersected by the radius.

Successful lookups are cached for 30 days. Provider requests are serialized per Worker isolate with at least 1.1 seconds between Nominatim request starts. Negative place lookups cache for a day; failures cache for one minute. A geocoder outage never stops a scan or invents a location name. Existing scans can resolve their location lazily; results and reviews are retained.

The area and each finding's review panel offer OpenStreetMap links at their actual coordinates. **OpenStreetMap itself is a map, not a street-view provider.** Panoramax's public federated catalog is checked within 150 meters; the nearest returned photo inside that radius enables a **View nearby street-level photo** button. The UI shows distance and capture date where supplied. Photo availability does not mean the object is visible from that camera position. No photo, a provider failure, and verified nearby coverage are separate states. Street imagery lookups cache for a day (failures for one minute).

Google Street View and Mapillary links are also available as explicitly unverified coverage checks. They need no credentials in the app, but coverage and third-party access can vary. External links open separately with `noopener noreferrer`; no API/worker credentials are included. No photo previews or third-party pages are embedded into the private app.

References: https://docs.panoramax.fr/web-viewer/03_URL_settings/ and https://docs.panoramax.fr/backend/api/api/ . Place names © OpenStreetMap contributors, ODbL. Ground photos retain their provider's metadata and licensing in the external viewer.


### Living Organisms (analysis v5)

The GUI uses Land Mammals, Aquatic/Marine Animals, Reptilian Creatures, Humans, and Unclassified Wildlife. Legacy species-based scans remain readable. Marine and reptile categories currently provide manual marking/review only, not automatic specialist classification. General COCO land-animal and person detection remains experimental on satellite imagery.

Optional OWL-C from [Microsoft MegaDetector-Overhead](https://github.com/microsoft/MegaDetector-Overhead) adds an aerial-trained point localizer. A checkpoint is downloaded to the ignored `.runtime/models` cache and verified against its pinned size and SHA-256 before loading. Code attribution is in `backend/third_party/owl_c`. **Weights are CC BY-NC-SA 4.0 (noncommercial/sharealike), distinct from MIT model code.** Preserve attribution and comply with the weights license when using or redistributing results. See [model release](https://zenodo.org/records/20802844).

Possible wildlife means a single-model candidate; probable means spatial agreement between general animal detection and the aerial locator. Human flags and category assessments are stored separately. Neither flag is a calibrated probability or confirmation. OWL-C activation is stored as localizationScore, never confidence; fixed review windows are not animal outlines or body dimensions. Actual inference was smoke-tested on an official aerial sample; AVIE satellite accuracy improvement has **not** been measured. Zero detections does not demonstrate absence.

Additional training candidates (not trained into AVIE): [WAID aerial wildlife](https://github.com/xiaohuicui/WAID), [Whales from Space](https://www.bas.ac.uk/data/our-data/publication/whales-from-space-dataset-an-annotated-satellite-image-dataset-of-whales-for-training-machine-learning-models/), [UAV crocodile imagery](https://datadryad.org/dataset/doi%3A10.5061/dryad.s4mw6m98n). Specialist training requires suitable imagery, data-license review, and held-out species/site validation. Marine/reptile training sets do not automatically add model classes.


### Archaeology, dedicated aerial human search, and reviewed examples (v6)

`Archaeology / structure remnants` runs coordinate-independent, multiscale contrast/stone-shadow cluster proposals. It flagged the central Stonehenge stone cluster in a reproduced 100 m-radius Esri image. These are exploratory structure candidates, not a trained archaeological-site classifier; human origin, age, and significance remain unconfirmed. It can miss buried sites, earthworks, walls, and crop marks; rocks, trees, paths and modern objects can be false positives. Known OSM historic features are a **separate** layer (`mapped-heritage`, `isImageDiscovery: false`), never counted as image discoveries. Map coverage may be incomplete or unavailable.

Humans can use the dedicated [YOLOv8s-VisDrone model](https://huggingface.co/mshamrai/yolov8s-visdrone), pinned to commit `996db9c3fbdf92ecdcf58411449a39232bfbcff6` with SHA-256 verification. Its model card declares OpenRAIL; VisDrone research-data terms and Ultralytics licensing apply. This is a third-party aerial-trained model, not a newly trained AVIE model. It searches 320 px crops with 25% overlap at 960 px inference size, with its own 15% default threshold. Magnification does not add source detail. Person and people/group outputs are suggestions, not a census or confirmed presence. On one reproduced Stonehenge scene, the earlier whole-tile COCO pass yielded zero, versus three deduplicated possible-person boxes from the new layer. This single-scene comparison is not a measured accuracy/recall improvement across sites. The provider fell back from requested level 20 to supported level 19.

Analyze any finding → **Cut & label training example**. For a missed person, draw a tight region using Mark feature first. Native crops (maximum 512 px per side) can be labelled human / not-human or structure-remnant / not-structure, with explicit human-review acknowledgement. Private R2 records retain source bounds, normalized positive boxes, coordinates, attribution, scan lineage, and notes. The library supports review, deletion, and ZIP export. A reviewed label is not independently established ground truth, and saving an example never retrains the engine automatically.

To prepare a custom human training candidate, after verifying source imagery training/reuse rights:

```sh
PYTHONPATH=backend python backend/train_people.py avie-reviewed-examples.zip --output .runtime/custom-human-data --rights-confirmed
# Add --train --device cpu (or an available accelerator) to fine-tune YOLOv8s.
```

Preparation requires at least 20 reviewed positive and 20 negative crops, across at least three independent geographic groups. Crops within 1 km or sharing scan ancestry stay together before train/validation splitting. These are minimum safeguards, not proof of adequate sample diversity. Candidate weights are **not activated automatically**. Validate independent-site precision/recall and false positives, and obtain suitable high-resolution imagery before promotion. No custom human model has been trained from the current small example set.

Archaeology research candidates include [Enki](https://github.com/archeorosati/enki) (primarily tell/mound imagery, not a universal stone-circle detector) and [Microsoft HERITAGE](https://github.com/microsoft/HERITAGE) (monitoring known archaeological sites, not a universal discovery model). They have not been trained into AVIE. LiDAR/terrain and multispectral data may be needed for subtle or buried remnants.


## GitHub layout

This current GUI/worker implementation is in `app/`, alongside the original CLI. Run the commands above from `app/` (for example, `cd app && npm run build`). Secrets, downloaded weights, private imagery, and scan history are excluded.
