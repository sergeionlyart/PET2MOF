# T014 numerical evidence

`T014-*.json` are small, project-transcribed numerical packets, not full articles.
Each quantity has units, source/extraction IDs, conditions, classification, limitations
and a JSON-pointer `evidence_ref`. Derived entries name their operands in `derived_from`;
an unqualified operand belongs to the same extraction, `extraction_id:key` to another.
The arithmetic is independently exercised by `tests/test_sourced_ranges.py`.

The corresponding passports in `../records/` use the existing extraction schema.
`derived_sha256` hashes the **whole packet file, including its final newline**.
`params.output_ref` names that file. `params.input_ref` / `input_sha256` identify the
original source bytes; `region` records the inspected render and its hash. No figure
coordinates were measured. All numerical records remain provisional.

`inputs.json` lists permitted acquisition URLs and exact input hashes. The original
PDF/HTML/XML files and renders are kept locally under `private/T014/`, excluded from Git.
They must be reacquired legally for an independent primary-source check; a dynamic HTML
hash mismatch is not permission to silently update a passport. Check the content/version
and record the replacement explicitly. Do not substitute an access-check HTML page for
a PDF. Crossref responses for new literature are in `sources/metadata/`.

For S119 the input is the original PMC HTML, not a PDF. The HTML section matching
`<section ... id="T2" ...>...</section>` was extracted unchanged and rendered using
`pymupdf.Story`, on a 720 × 900 pt page with 36 pt margins, then rasterized at scale 1.5.
Its logical rendered page is 1. The table layout is simplified by the renderer; source
DOM column structure and the visible tertiary-amine column were both checked. No table
numbers were manually inserted into the rendered source. Other renders use the original
PDF page at scale 1.5; repository S106 has a cover sheet, accounted for in its locators.

`design_basis.json` pins existing project files used to retain stress bounds. Its
passport is explicitly a transcription of design assumptions, **not experimental data**.
The schema has no `assumption_range` data-kind enum, so that passport uses `text_value`
with `params.not_a_measurement: true`; parameter-level `type` is authoritative. Page 1
means the logical design manifest. No DOI is invented for this project source.

T020: the journal hash in this historical manifest covers decisions through D-17,
before D-18 was appended. The test checks that exact prefix (one final newline),
without changing the evidence packet or its accepted passport. The current whole
journal, including D-18, is separately hashed by the final frozen calibration.

Validation, from repository root:

```sh
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked --no-sync pytest tests/test_sourced_ranges.py -q
```

The test always checks the registry joins, packet hashes, schema, existing configuration
loader, conversions, signed humidity effects, unknown target values and design origin.
It also checks original/render hashes when those local files are available. No network,
holdout data, paid OCR, API secrets or model execution is needed. Passing this test does
not independently verify the transcription or physical transferability.
