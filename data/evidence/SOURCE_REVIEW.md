# Data source review — 2026-11-12

Reviewed official web pages and repository metadata in this session, without downloading any dataset bytes.

| Source | Observation | Limit |
|---|---|---|
| https://synthetichealth.github.io/synthea/ | Official project explains synthetic data and provides FHIR R4/CSV sample links; broad research/privacy-use statements | Does not resolve all artifact-specific redistribution/training/code-system conditions for the selected archive |
| https://synthetichealth.github.io/synthea-sample-data/downloads/synthea_sample_data_fhir_r4_sep2019.zip | Exact official-page download target | Web retrieval timed out; no bytes retained, no SHA-256 or retrieved_at |
| https://api.github.com/repos/synthetichealth/synthea-sample-data/contents/downloads | Metadata identifies selected archive: 85,042,887 bytes; Git blob SHA 638548126fdfbad63dfc1bd4dd940e3af82e5251 | Git blob SHA is not downloaded-file SHA-256; metadata is not artifact inspection |
| https://api.github.com/repos/synthetichealth/synthea-sample-data/contents/ | Root listing has downloads, index.html and .nojekyll | No LICENSE in this root listing; absence is not a legal conclusion |
| https://api.github.com/repos/synthetichealth/synthea-sample-data/contents/LICENSE | 404 observed | No inferred dataset license from Synthea generator Apache-2.0 |
| https://github.com/synthetichealth/synthea/wiki/Frequently-Asked-Questions | Official FAQ distinguishes modeled synthetic data from real/de-identified data and describes limits of representativeness | Not an effectiveness benchmark for HIS or Thai hospitals |
| https://mitre.github.io/fhir-for-research/modules/synthetic-data | MITRE describes static synthetic data and research/testing use | Ophthalmology/image artifacts have separate conditions; none downloaded or bundled |

Decision: keep selected Synthea artifact metadata-only (NOT_DOWNLOADED/NOT_BUNDLED), with cloud processing, redistribution and model-training permission statuses UNKNOWN at artifact level. This is the bounded fallback explicitly allowed by OPEN_DATA_PLAN. New Thai fixture content and reproducibility are completed independently. MIMIC and real/de-identified patient datasets are not used.

External page retrieval is evidence of reviewing the page on 2026-11-12, not a record of downloading the ZIP. Publisher statements are paraphrased; no full page or third-party dataset is redistributed here.
