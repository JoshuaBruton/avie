# A.V.I.E.
[**Anomaly Vision Intelligence Engine**] - A geospatial computer-vision pipeline that retrieves satellite imagery for selected coordinates, runs YOLOv8 object detection, and logs potential findings for review. Expanding toward systematic area scanning and anomaly analysis.



## Features
- Accepts coordinates and radius value
- Random coordinate generation within radius
- Satellite image downloading via Google Static Maps API
- Object detection using YOLOv8
- Flagging and saving anomalies


## Current interactive application

The current dark satellite-analysis GUI, persistent scan API, and Python worker are in **[app/](app/README.md)**. The original CLI scripts remain available.

The app includes overlapping-tile satellite analysis, structure/remnant candidates, dedicated aerial human detection, wildlife categories, mapped agriculture and heritage context, saved reviews/history, close-up rescans, and reviewed training-crop export. Image candidates are unconfirmed; known map records are labelled separately. No detector identifies every person or archaeological site.

See [app/README.md](app/README.md) for setup, licensing, and limitations, and [app/VALIDATION.md](app/VALIDATION.md) for verification evidence. Custom human training needs reviewed positive/negative examples and independent-site validation; it does not run automatically. Credentials and downloaded model weights are excluded.
