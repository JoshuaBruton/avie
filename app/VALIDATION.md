# Publication status: resolved

The update was published successfully to the private AVIE Site; its Python worker is online at analysis version 6. The authentication issue below is historical. Source snapshot: 847077f8a2cd8775d34fa1a2e862c8850cac27fd.

# Discovery update: validation and publication status

Implemented locally against the last published source commit `0491d38864639feb140603259cc7bdc603a8a07d` (Sites version 10). The current Sites version list confirms that source base. Publication has not occurred.

## Observed evidence

- Reacquired Esri imagery at 51.1788497418401, -1.8261780912839 with 100 m radius. The provider supported zoom 19 rather than requested 20; mosaic 1070 x 1070, sampled 0.187 m/px. Native source detail is not established by sampling.
- The previous general person pass returned zero boxes in the reproduced scene. Dedicated VisDrone aerial inference on overlapping 320 px crops returned three deduplicated possible-person boxes after radius filtering, at a separate 15% threshold. Some visitors remain missed. No held-out satellite accuracy or complete population count is claimed.
- Coordinate-independent contrast-cluster proposals flagged the central stone cluster (two overlapping candidates). No name, hard-coded location, or map tag is used by this image proposal function. Age and human origin remain unconfirmed; natural and modern lookalikes may be included.
- OpenStreetMap separately supplied Stonehenge as a known historic feature. It is marked `isImageDiscovery: false`. This is existing map context, not a newly discovered site.
- 14 Node API/geocoding tests and 21 Python tests passed. Tests cover new settings, source separation, human tiling/NMS, reviewed-example validation/persistence, training split grouping, and prior behavior.
- Desktop/mobile browser validation used the real output in a local Worker/R2 test adapter. It verified filters, native crop cutting, required review acknowledgement, private library save/view/delete, ZIP integrity and source metadata, settings, all-target subcategory selection, and close-up inheritance. The local adapter is not production hosting and uses test-only authentication.

## Custom human training status

The active enhancement implemented here is a third-party aerial-trained model, not a custom AVIE model trained from Stonehenge. Reviewed human/negative crops can be exported and used by `backend/train_people.py`. Minimum sample/site guards and grouped validation prevent treating repeated crops from one location as independent validation. No custom model has been trained or activated; no examples were added to the production library during local QA. Verify imagery training/reuse rights before training. Model/data licensing is documented in README.

## Publication blocker and resumption

Sites now returns a `codex_auth` repository URL at `https://chatgpt.com/backend-api/codex/sites/git/appgprj_6af4bab0e944819184d89bd765b69836`. Ordinary Git access returns HTTP 400 with `missing_account_user_id: Unable to determine account user id.` The required host-supplied Sites Git credential helper is unavailable in this executor. Refreshing the native source credential did not change that result. Do not bypass authentication or publish an archive against an unpushed source SHA.

Restore the host's Sites Git authentication, obtain a fresh repository credential for the same project, synchronize/push this source, then publish the matching built archive with owner-private access preserved. Refresh ownership/audience first. Restart the Python worker with its existing secret configuration only after confirming no scan is active; backend v6 must be paired with the new API/GUI. The existing remote worker has not been restarted, and the existing live Site remains at version 10. No AWS deployment has been made by this change.
