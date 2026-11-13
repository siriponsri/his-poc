# Frontend reference review

Reviewed: 13 November 2026. Scope: information architecture and visual inspiration; not a product evaluation or clinical benchmark.

| Source inspected | Observation | Adaptation |
|---|---|---|
| [HIS_Frontend / MedFlow](https://github.com/YomnaSabry172/HIS_Frontend) | README describes a frontend simulation with grouped workspaces and patient search; backend/auth/persistence appear in its roadmap. | Shared tokens, grouped navigation and consistent record/detail layouts. Retain this project's existing server-backed workflows. |
| [SoftwareSuggest HIS overview](https://www.softwaresuggest.com/blog/top-hospital-information-system/) | Editorial roundup covers records, scheduling, billing, inventory and portals. | Coverage reminder; separate clinical, financial and operational areas. Vendor claims, prices and rankings were not independently validated. |
| [AdminLTE healthcare dashboards](https://adminlte.io/blog/healthcare-dashboard-templates/) | Distinguishes templates, applications and developer platforms, plus clinical/operational/financial audiences. | Task-focused home and visible clinical context. A template does not establish backend functionality or compliance. |
| [Worldmetrics HIS roundup](https://worldmetrics.org/best/his-software/) | Discusses workflow coverage, history and reporting with editorial rankings and commercial disclosures. | Preserve status/history/evidence access. This is discovery material, not verified comparative or clinical performance. |

All four sources were accessible during this bounded review. MedFlow main resolved to d140e253583b92432e51a25117292cdaf0483ab5. Its README claims MIT, but no standalone LICENSE appeared in the root listing and the raw main/LICENSE returned404; full terms were not verified. No source code or assets were copied.

The supplied screenshots guide whitespace, fine dividers, clinical workspaces and warm accents. The Medplum example supplies a restrained purple identity; the monochrome overview suggests alignment; the peach/lavender task view suggests grouping; the purple/orange marketing image supplies color relationships. Unnamed images are not attributed to invented authors or redistributed as artwork.

The owner explicitly chose yellow, gray, purple and orange. Warm gray is the canvas, white is the working surface, purple identifies primary actions, yellow identifies selected navigation and orange draws attention. Status text/icons remain necessary. No invented KPI, decorative chart, simulated result or competitor logo was added. Existing API/auth/scope, approvals, retry keys and real dr-train behavior remain authoritative.
