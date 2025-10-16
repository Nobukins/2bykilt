# CSV Preview Feature

This document describes the CSV Preview feature implemented for batch processing.

Overview
- Shows top-N rows of an uploaded CSV in the UI.
- Detects a candidate unique-id column and surfaces it in a dropdown for user override.
- Requires the user to press "Confirm Preview" to enable the "Start Batch Processing" button when the feature flag is enabled.

Feature flag
- The preview is gated by the feature flag `feature.csv_preview`.
- To enable in production, toggles should be adjusted in the feature flags configuration. During development the default may be set to `True`.

How it works (high level)
1. User uploads a CSV (drag & drop or file picker).
2. The client triggers a change event; server parses the CSV using `src.batch.csv_utils.parse_csv_preview`.
3. A detected unique-id column is selected via `_detect_unique_candidate` and placed at the left for visibility.
4. The preview table shows the top-N rows plus a `_job_template` column that reflects the selected template.
5. User can override the unique-id column using the dropdown. Changing inputs resets preview confirmation.
6. User clicks `Confirm Preview` to enable the `Start Batch Processing` button.

Notes for developers
- Parsing is implemented in `src/batch/csv_utils.py` to centralize encoding/format handling.
- UI wiring and gating live in `bykilt.py` (see the `📊 Batch Processing` tab code).
- The development default for the feature flag may be set in `bykilt.py` for local testing; in production rely on the project's feature flag management system.

Testing
Manual: run the UI and upload a CSV to verify preview, change the preview rows slider, override the unique column, and confirm preview before starting.
Unit: consider adding a unit test for `parse_csv_preview` and a small wrapper test for `preview_csv_fn` to verify returned DataFrame structure.
