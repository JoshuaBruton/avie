# AVIE validation and deployment status

Documentation reviewed on 2026-11-13 against source commit
`9186df6546a30589304c65ea226619744bc4b30f` (imagery policy v7).
This record separates repository checks from historical experiments and live deployment.

## Current repository verification

The following checks passed in the managed development environment on 2026-11-13:

| Scope | Command | Result |
| --- | --- | --- |
| Web bundle (from `app/`) | `node build.mjs` | Worker and six assets built |
| Web API/policy/place lookup (from `app/`) | `node --test tests/*.test.mjs` | 20 passed |
| Python backend (from `app/`, backend dependencies installed) | `PYTHONPATH=backend python -m unittest discover -s backend -p 'test_*.py'` | 24 passed |
| Original CLI (from repository root) | `python -m unittest discover -s tests -v` | 5 passed |

Build before the Node tests: API tests import the generated Worker bundle.
Backend checks used the prepared `/workspace/.venvs/avie` Python environment;
the system Python does not contain the inference dependencies.

Coverage includes API authentication, queue leases, cancellation, persistence,
reviews, exports, target settings, location/street-photo lookup states, private
aerial imports, dimensions and footprint containment, capture-date precision,
worker compatibility, imagery eligibility, native zoom limits, detector routing,
mapped-evidence separation, human tiling/deduplication, and reviewed-example
validation and grouped training preparation. Context-only scans are tested to
skip image detectors; unsupported detailed results from old workers are filtered.
These are software checks, not field measurements of precision or recall.

## Current imagery and model boundary

- Detailed inference requires declared native aerial GSD ≤5 cm/pixel, delivered
  spacing ≤5 cm/pixel, source/licence metadata and explicit analysis/display
  permissions. Provider evidence must establish these claims; flags alone cannot.
- Esri is context imagery. Current policy reports
  `not_run_insufficient_imagery` for detailed inference, rather than a successful
  zero-detection scan. Historical observations retain their original timestamps
  and are labelled unverified.
- Capture date/time remains distinct from analysis time. Unknown dates stay
  unavailable; date-only and range values retain their precision.
- No qualifying Stonehenge baseline has been purchased or verified. No independent
  people/wildlife detection accuracy or complete survey has been established.
- Custom AVIE human weights have not been trained or activated. Exported reviewed
  crops are user labels, not independently established ground truth. Imagery
  training/reuse rights and held-out geographic validation are required before
  promoting a training candidate. See [README.md](README.md) for model licences.

## Historical experimental evidence

Before the v7 imagery gate, a reproduced Stonehenge Esri scene at
51.1788497418401, -1.8261780912839 used a 100 m radius. Requested provider zoom 20
fell back to 19; the 1070 × 1070 mosaic had sampled spacing of 0.187 m/pixel.
Sampling did not establish native capture GSD or usage rights.

The earlier general person pass yielded zero boxes; dedicated third-party
VisDrone inference yielded three deduplicated possible-person boxes at a separate
15% threshold. Some visitors remained missed. This single-scene experiment does
not establish accuracy or recall across sites and does not satisfy today's
imagery eligibility requirements.

Coordinate-independent contrast-cluster proposals flagged the central stone
cluster as two overlapping candidates. Human origin, age and significance were
not established by the algorithm. OpenStreetMap separately supplied Stonehenge
as a known historic feature (`isImageDiscovery: false`); it was not a discovery.

Earlier local browser validation covered desktop/mobile review, crop cutting,
review acknowledgement, private library save/view/delete, ZIP integrity,
settings, target inheritance, missing-baseline messaging, historical dates and
native zoom using isolated local fixtures/adapters. Those records are retained
as historical QA evidence; browser checks and real inference were not rerun in
this documentation-only update.

## Deployment status and next verification

Prior notes recorded a private Site publication with worker analysis version 6,
then v7 source integration. They also contained an older Sites Git-authentication
failure and conflicting publication statements. Neither establishes the current
live frontend or external worker version. Live deployment was not inspected or
changed in this documentation update.

GitHub source push, Sites frontend/API publication, and external Python worker
deployment are separate operations. Publishing the Site does not restart the
Python host. For a v7 rollout:

1. Publish the matching built frontend/API while preserving private access and R2.
2. Deploy `app/backend/` on the existing Python host/container with its existing
   secret configuration and persistent model volume; avoid interrupting active jobs.
3. Check authenticated `/api/health`: `worker.analysisVersion` must be at least 7
   and the heartbeat must be current before licensed aerial imports can proceed.
4. Verify a licensed baseline and a context-only scan, capture metadata, saved
   review/history and export behavior in the deployed environment.

No current hosting outage is inferred from historical authentication failures.
No imagery procurement, production model training, or deployment is performed by
this documentation change.
