# SCAN Legacy — Smart Computational Analyzer for Nanosensors
## Blueprint & Technical Specification (Legacy / Prototype Edition)

Version 1.0 — July 2026
Prepared for: solo-vibecoded prototype build, publication-driven timeline

---

## 0. Why This Document Exists

The original SCAN Blueprint v1.0 specified nine integrated modules across eight build phases (27+ months, multi-tenant SaaS, mobile app, robotic fabrication hooks, full regulatory hub). An audit against the actual repository showed ~15% real completion after significant effort, with zero of the platform's own "non-negotiable engineering rules" implemented. That scope was never buildable by one person on a publication timeline.

This document replaces it. **SCAN Legacy** keeps the original vision's scientific core — a trustworthy, explainable, physics-grounded research companion for nanosensor development — and cuts everything that isn't required to prove that core works. Four modules. One shared trust layer. One physics layer. A stack that deploys in days, not months.

**Guiding principle for every decision in this document:** if a feature can't be built with the data actually on disk, or doesn't serve the goal of a defensible, reproducible, physically-plausible prediction, it does not belong in v1. Park it, don't build it.

---

## 1. Core Identity

| | |
|---|---|
| **Name** | SCAN Legacy |
| **Type** | Single-tenant-first web application (multi-user, not multi-org) |
| **Primary purpose** | Publication-ready prototype demonstrating physics-constrained, uncertainty-honest ML for nanosensor research |
| **Primary users** | You + a small number of contributors/reviewers (advisor, co-authors, lab colleagues) |
| **Platforms** | Web only (React SPA). No mobile app in v1. |
| **Deployment target** | Cloudflare Pages / Vercel (frontend) + Railway or Render (API + Postgres) |
| **Explicit non-goals for v1** | Multi-tenant SaaS, robotic fabrication integration, EU REACH/FDA/ISO regulatory hub, mobile app, community peer-review marketplace, literature-mining NLP pipeline, digital twin / edge-AI latency sandbox |

---

## 2. Modules — Scope Table

| # | Module | What's In | What's Explicitly Out (v1) |
|---|--------|-----------|------------------------------|
| 1 | **Shared Data Dashboard** | Structured entry, versioning, review gate, provenance, data health panel | Free-text entry, silent overwrite, org-level permission matrices |
| 2 | **Design Studio** | Material Explorer (search/browse) + Inverse Design as **retrieval-ranking**, not generative DNN | Generative inverse-design DNN, cost/resource estimator, literature/patent AI scan |
| 3 | **CV/LSV + EIS Analyzer** | Physics-first deterministic extraction (Randles-Sevcik, Nicholson, Cottrell, Randles-circuit fit), overlay/compare, calibration curve builder | Universal auto-format-detection across all vendors, drift RL compensator, robotic protocol generation |
| 4 | **XAI Dashboard** | SHAP explanations, confidence tiers, physical-plausibility flags, standardized across all modules | Free-form causal-language explanations |
| 5 | **Team Workspaces & Access Control** | 3 roles (Owner/Contributor/Viewer), simple auth | Institutional hierarchy, per-dataset granular permission matrix, billing |

Modules 1, 3, and 4 are buildable today with data already on disk. Module 2's retrieval-ranking is buildable today. Module 3's physics layer is buildable today; its ML layer waits on either real or simulated CV/EIS traces (Phase 2 of this document covers both paths).

---

## 3. Data Inventory & Sourcing Plan

### 3.1 What you already have (confirmed on disk)

| Dataset | Rows/Files | Use | Status |
|---|---|---|---|
| nanoPharos | 57 files | Toxicity training (Module 1 + 2) | ✅ Ready |
| Zenodo MeOx | 15 samples | Toxicity training, mandatory LOO-CV | ✅ Ready |
| Zenodo SAPNet | 29 samples | pEC50 training, mandatory LOO-CV | ✅ Ready |
| Zenodo Trinh mixture | 183 samples | Toxic/non-toxic classification | ✅ Ready |
| caNanoLab | 900 rows | Material metadata enrichment | ✅ Ready |
| UCI drift | 13,910 rows | **Out of scope for v1** (gas sensor, not electrochemical) — retain for future module | Staged, not used |
| MassBank | large | **Out of scope for v1** (spectral) | Staged, not used |
| RRUFF | large | **Out of scope for v1** (Raman/XRD) | Staged, not used |
| SEM images | 28 TIFs | **Out of scope for v1** (morphology) | Staged, not used |
| XPS spectra | present | **Out of scope for v1** | Staged, not used |
| CV/LSV/EIS raw traces | **0 files** | Module 3 core input | ❌ Gap — see 3.2 |

Do not force the staged datasets into v1 modules. They stay in `data/raw/` labeled "acquired, out of scope" for a future phase.

### 3.2 The CV/LSV/EIS data gap — resolution plan

Real raw electrochemical traces are rarely published; papers report extracted numbers, not raw files. Plan, in priority order:

1. **Simulate first, this week.** Generate synthetic CV curves from the Randles-Sevcik equation and synthetic EIS spectra from a Randles equivalent circuit (Rs + Rct ‖ Cdl + Warburg element), each with realistic Gaussian noise and baseline drift added. This gives known ground truth to validate the parser against — a legitimate, citable validation methodology, not a placeholder.
2. **Acquire real traces where possible.** Any lab access — your own, borrowed, or a collaborator's — even 5–10 real CV/EIS runs meaningfully de-risks the parser and lets the paper claim real-world validation, not just simulated.
3. **Targeted search for public raw traces.** Zenodo, Mendeley Data, Figshare — search "raw cyclic voltammetry data" / "raw EIS data" + target analyte. Treat as opportunistic, not load-bearing.
4. **Manual literature curation for the performance database.** Hand-curate 20–30 papers' worth of extracted LOD/sensitivity/linear-range numbers into the shared dashboard (Module 1). This feeds Module 2's retrieval-ranking. Full NLP literature-mining automation (ChemDataExtractor/OSCAR4) is explicitly deferred — it's a serious project on its own.

### 3.3 On EIS Gold Studio (existing desktop tool)

The existing `.exe` is a PyInstaller bundle with no accessible source — its compiled `.pyd` files cannot be imported or reused directly. Action items:
- Check whether original `.py` source exists anywhere outside the built bundle. If it does, treat it as a real candidate for porting logic into the FastAPI backend.
- If no source exists, use the tool only as a **validation reference**: run the same raw trace through both EIS Gold Studio and SCAN Legacy's new analyzer once built, and compare outputs as a sanity check.
- Do not spend build time attempting to decompile or reverse-engineer the binary.

---

## 4. Foundational Architecture

### 4.1 Principles

- **One backend, one database.** No microservices split for v1.
- **No premature infrastructure.** No Redis, no Celery, no message queue until there is an actual scheduled job that needs one.
- **Physics before ML, always.** Deterministic equation-based calculators run first; ML only operates on top of physically-derived features or fills gaps equations can't cover.
- **One trust envelope, shared everywhere.** Every prediction from every module returns the same structured response shape — no per-module reinvention.
- **Reproducibility is a hard requirement, not a nice-to-have.** Every prediction must be traceable to the exact dataset version that produced it.

### 4.2 Repository structure

```
scan-legacy/
├── apps/
│   └── web/                     # React + Vite + TypeScript SPA
├── api/                         # FastAPI backend, single service
│   ├── app/
│   │   ├── main.py
│   │   ├── auth/                # JWT auth, roles
│   │   ├── routers/             # one file per module's endpoints
│   │   ├── schemas/             # Pydantic models — the canonical trust envelope lives here
│   │   ├── db/                  # SQLAlchemy models, session, migrations (Alembic)
│   │   └── core/                # config, security, dependencies
│   ├── ml/
│   │   ├── physics/             # deterministic equation-based calculators (see Section 5)
│   │   ├── models/               # trained ML models (cytotoxicity, pEC50, ranking)
│   │   ├── training/             # LOO-CV enforced training scripts
│   │   └── shared/                # confidence tiering, SHAP wrapper, plausibility rules
│   └── tests/
├── data/
│   ├── raw/                     # unchanged, includes staged out-of-scope sets
│   ├── processed/               # cleaned, versioned training sets
│   └── simulated/               # physics-simulated CV/EIS traces (new)
├── docs/
│   └── SCAN_Legacy_Blueprint_v1.0.md   # this file
├── docker-compose.yml            # Postgres only, plus API service
├── .env.example
└── requirements.txt
```

No `packages/shared` as a separate publishable package — for a 4-module solo build this is overhead. The trust envelope schema lives once in `api/app/schemas/` (Pydantic) and is mirrored by hand into a small `apps/web/src/types/` file (Zod schemas) — small enough at this scope to keep in sync manually, revisit if the team grows.

### 4.3 Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Vite + TypeScript | Lean SPA, no SSR complexity you don't need |
| UI state/data | TanStack Query | Caching, refetch, avoids hand-rolled fetch+useState sprawl |
| Forms/validation | React Hook Form + Zod | Mirrors backend Pydantic validation |
| Backend | FastAPI (Python 3.11) | Async-native, auto OpenAPI docs, natural fit for ML serving |
| Database | PostgreSQL 16 | Relational integrity; pgvector extension available if similarity search is added later for retrieval-ranking |
| ORM/migrations | SQLAlchemy + Alembic | One ORM, no dual-stack (dropping Prisma from the original plan — Python-only backend doesn't need a JS ORM) |
| Auth | JWT (access + refresh), passwords hashed with bcrypt | Simple, no NextAuth needed since this isn't Next.js |
| ML — classical | scikit-learn, XGBoost | Cytotoxicity, pEC50, ranking |
| ML — explainability | SHAP (TreeExplainer) | Standardized across all models |
| Physics/curve fitting | scipy.optimize, numpy | Randles-Sevcik, Nicholson, Cottrell, Randles-circuit fitting |
| Plotting (backend-generated) | matplotlib (server-side) or Plotly (client-side, preferred for interactivity) | Nyquist/Bode plots, CV overlays |
| Background jobs | None in v1 | Add only if a real nightly-retrain need appears |
| Deployment — frontend | Cloudflare Pages or Vercel | Static SPA, fast, free tier sufficient |
| Deployment — backend + DB | Railway or Render | Single deployable API + managed Postgres |
| CI | One GitHub Action: lint + test on push | Enough to catch regressions, not a full pipeline |

---

## 5. Physics Layer (`api/ml/physics/`)

This is new relative to the original blueprint and is now foundational, not optional. Its purpose: constrain small-data ML with known chemistry/physics so the app never produces confident nonsense.

### 5.1 Deterministic calculators (no ML, pure equations)

| Calculator | Equation | Input | Output | Used by |
|---|---|---|---|---|
| Randles-Sevcik | ip = (2.69×10^5) n^(3/2) A D^(1/2) v^(1/2) C | peak current, scan rate, electrode area | diffusion coefficient D | Module 3 |
| Nicholson method | ΔEp vs. ψ function | peak separation, scan rate | heterogeneous electron transfer rate constant k⁰ | Module 3 |
| Cottrell equation | i(t) = nFAD^(1/2)C / (π^(1/2) t^(1/2)) | current-time transient | diffusion-limited current, LOD from S/N | Module 3 |
| Randles equivalent circuit fit | Z(ω) = Rs + (Rct·(1/(jωCdl))) / (Rct + 1/(jωCdl)) + Warburg | EIS frequency sweep | Rs, Rct, Cdl, Warburg coefficient | Module 3 |
| Stokes-Einstein | D = kT / (6πηr) | particle radius, viscosity, temperature | hydrodynamic diffusion coefficient | Module 2 feature engineering |
| Surface-area-to-volume ratio | SA/V from core geometry | core size | reactivity-correlated feature | Module 2 feature engineering |
| Debye-Hückel correction | ionic-strength-corrected zeta potential | raw zeta reading, buffer conditions | comparable zeta potential across conditions | Module 2 feature engineering |

Implementation rule: these are pure functions in `api/ml/physics/`, unit-tested against known textbook values before anything else in Module 2 or 3 is built. They are calculators, never trained parameters.

### 5.2 Physical plausibility rules engine (`api/ml/shared/plausibility.py`)

Sits between any ML model's raw output and what the API returns. Examples of rules to implement:

- Toxicity/dose-response monotonicity: reject or flag a prediction where higher exposure predicts lower toxicity for the same pathway.
- LOD predictions bounded by the theoretical detection limit implied by Faraday's law for the given electrode area/scan rate.
- Zeta potential predictions outside ±100 mV (the practically observed range) flagged as out-of-distribution.
- Any prediction for a material/analyte combination physically incompatible with the sensor's transduction type (e.g., an EIS-only feature requested for an optical sensor input) is rejected outright, not silently computed.

Output of this stage is a field: `physical_plausibility: "pass" | "flagged" | "fail"`, always attached to the trust envelope (Section 6).

---

## 6. The Shared Trust Envelope

Every prediction, from every module, returns this exact structure. Defined once in `api/app/schemas/prediction.py`.

```python
class PredictionEnvelope(BaseModel):
    value: float | dict                # the prediction itself
    confidence_tier: Literal["LOW", "MEDIUM", "HIGH"]   # <50 / 50-500 / >500 samples
    uncertainty_range: tuple[float, float]               # 5th-95th percentile via bootstrap
    training_data_count: int
    shap_values: dict                                    # feature: attribution
    physical_plausibility: Literal["pass", "flagged", "fail"]
    dataset_version_id: str            # exact snapshot used — reproducibility
    model_name: str
    model_version: str
    trained_at: datetime
```

### 6.1 Hard rules (enforced in code, not convention)

1. Any model trained on <50 samples MUST use Leave-One-Out cross-validation. Enforce this inside a single shared training utility (`api/ml/training/base_trainer.py`) that all model training scripts call — never let an individual script decide.
2. `training_data_count` < 50 → confidence_tier is always LOW, displayed with an explicit "insufficient data for reliable prediction" state in the UI — never a bare number with a small disclaimer.
3. Every prediction stores `dataset_version_id`. Re-running a prediction request against the same `dataset_version_id` and `model_version` must return an identical result.
4. SHAP language in the UI: "the model weighted these features most heavily," never "this is why" — SHAP is attribution, not causal proof.
5. `physical_plausibility: "fail"` predictions are never displayed as a clean number — the UI must show the flag prominently, not as a footnote.

---

## 7. Module 1 — Shared Data Dashboard

### 7.1 Purpose
The backbone. All training data for Modules 2 and 3 lives here, structured, versioned, and reviewed before it's trainable.

### 7.2 Data model (new tables beyond the original blueprint's MLPrediction/User)

- `material_records` — structured nanomaterial entries (core_size_nm, zeta_potential_mv, surface_area_m2g, coating, material_type, source_type, doi, contributor_id, extraction_confidence)
- `toxicity_records` — links to material_records, IC50/EC50/pEC50, cell_line, exposure_time_h
- `sensor_performance_records` — nanomaterial, analyte, lod_mol_per_l, sensitivity, linear_range, response_time_s, source_type, doi
- `record_versions` — every edit creates a new version row; never overwrite in place
- `record_reviews` — reviewer_id, status (pending/approved/rejected), notes, reviewed_at

### 7.3 Features

- **Structured entry forms** with unit dropdowns (not free text), physical-plausibility validation at point of entry (reuses Section 5.2's rules engine)
- **Versioning**: every edit stored as a new version with a diff view; nothing is hard-deleted
- **Review gate**: single-reviewer approve/reject before a record counts as "trainable"; unreviewed records visible but visually distinct and excluded from training by default
- **Provenance always visible**: source_type, contributor, DOI, extraction_confidence as persistent UI elements, not a hidden detail view
- **Data health panel**: live sample counts per material/analyte pair — directly informs confidence tiering elsewhere in the app
- **Duplicate detection on submit**: check by DOI + material/analyte combination at the moment of entry, not as a separate batch job
- **Export**: CSV/JSON download of the current approved dataset snapshot

### 7.4 Suggested additional dashboard features
- A simple "what's missing" view: material/analyte pairs with fewer than 5 samples, to guide where manual curation effort should go next
- An audit log view: who changed what, when — useful for the paper's reproducibility claims and for catching bad edits early
- A "model impact preview": before approving a batch of new records, show which models would be retrained and how sample counts would shift confidence tiers

---

## 8. Module 2 — Design Studio

### 8.1 Material Explorer
- Search/browse UI over `material_records`, backed by PubChem live API for analyte-side metadata (molecular formula, weight, xlogp, tpsa)
- Safety card view per material: toxicity prediction (via Module 1 data + trained model) with full trust envelope displayed

### 8.2 Inverse Design — reframed as retrieval-ranking
Per the critical analysis: a generative DNN is not supportable by ~230 labeled toxicity samples. Build instead:
1. User specifies target spec (e.g., LOD < 1 nM, analyte = glucose, matrix = blood)
2. System computes similarity between the target spec and every material in `material_records` + `sensor_performance_records`, using physics-derived features from Section 5.1 alongside raw features
3. Rank candidates by predicted fit using the same XGBoost + SHAP + confidence machinery as the toxicity model
4. Return top-N candidates, each with a full trust envelope — never a single "best answer" presented as certain

This is explicitly staged to upgrade to true generative inverse design once the community database has real volume — noted as a Phase 3+ (post-v1) goal, not built now.

---

## 9. Module 3 — CV/LSV + EIS Analyzer

### 9.1 Architecture: physics-first, ML-second
Stage 1 (physics, no training data required) — parse raw trace, apply Section 5.1 calculators, output real electrochemical parameters deterministically. Stage 2 (ML, uses Stage 1's outputs as training rows) — once enough traces have been processed, extracted parameters feed `sensor_performance_records` and support retrieval-ranking in Module 2.

### 9.2 Features
- **File ingestion**: support 1–2 real vendor formats you actually have sample files for (start with whichever format your simulated/real traces use); manual column-mapping fallback UI for anything else — no false promise of universal auto-detection
- **CV/LSV processing**: peak detection, Randles-Sevcik diffusion coefficient, Nicholson electron-transfer rate, Cottrell-based LOD with signal-to-noise
- **EIS processing**: Nyquist + Bode plotting, automatic Randles equivalent-circuit fitting (Rs, Rct, Cdl, Warburg) via scipy.optimize.curve_fit
- **Overlay/compare mode**: plot multiple CV curves (concentration series, batch comparison) on one axis
- **Calibration curve builder**: from a concentration-varied CV batch, auto-generate calibration curve with LOD/LOQ and confidence interval (not a bare point estimate)
- **Drift flag**: if the same electrode is re-run over time, flag baseline shift automatically — lightweight precursor to a future full drift-compensation module
- **Push-to-database**: processed results can be submitted directly into Module 1's dashboard as new `sensor_performance_records` rows, entering the review queue

### 9.3 Data path
Uses `data/simulated/` (Section 3.2, step 1) as the initial validation and development dataset; real traces (Section 3.2, step 2) layered in as available; both paths produce the same trace format so the parser doesn't need to know which source a file came from.

---

## 10. Module 4 — XAI Dashboard

### 10.1 Purpose
The credibility layer, visualizing what Section 6's trust envelope already computes. Not a separate prediction pipeline — a standardized view over it.

### 10.2 Features
- **SHAP waterfall chart** component, shared across cytotoxicity, pEC50, and Module 2 ranking predictions — one component, not reimplemented per module
- **Confidence badge** component: LOW/MEDIUM/HIGH, color-coded, with training_data_count shown alongside — same component used everywhere the trust envelope appears
- **Physical plausibility indicator**: prominent flag/warning state when `physical_plausibility != "pass"`
- **Model health view**: per-model training_data_count, last trained date, LOO-CV vs. train/test split used — transparency into what each model actually knows
- **Global model performance page**: aggregate view across all models, useful for the paper's methods/results section directly

---

## 11. Module 5 — Team Workspaces & Access Control

Deliberately minimal for v1.

### 11.1 Roles
- **Owner** — full access, only role that can approve/reject data reviews and manage other users
- **Contributor** — can add/edit data (enters review queue), run all modules, view everything
- **Viewer** — read-only, for advisors/reviewers to explore the demo

### 11.2 Explicitly out of scope
No institutional hierarchy, no per-team billing, no granular per-dataset permission matrix. Revisit only if the tool sees real multi-lab adoption post-publication.

### 11.3 Implementation
JWT-based auth (access token 15 min, refresh token 7 days), role stored on the user record, a single dependency-injected `require_role()` check in FastAPI routes. No separate auth microservice.

---

## 12. Build Phases — Step by Step

### Phase 0 — Foundation (Target: Week 1)
1. Initialize repo structure per Section 4.2
2. `docker-compose.yml` with Postgres 16 only (add pgvector extension if planning similarity search for Module 2 ranking)
3. FastAPI skeleton: `main.py`, health check endpoint, DB connection via SQLAlchemy
4. Alembic initialized, first migration: `users`, `material_records`, `toxicity_records`, `sensor_performance_records`, `record_versions`, `record_reviews`
5. `.env.example` with all required variables (DATABASE_URL, JWT_SECRET, PUBCHEM_BASE_URL, etc.)
6. `requirements.txt` committed (fastapi, uvicorn, sqlalchemy, alembic, pydantic, scikit-learn, xgboost, shap, scipy, numpy, pandas, python-jose, passlib[bcrypt])
7. React + Vite + TypeScript scaffold in `apps/web`, TanStack Query + React Hook Form + Zod installed
8. Auth: JWT register/login/refresh endpoints, bcrypt password hashing, role field on user model

**Validation:** `docker-compose up` runs clean; `alembic upgrade head` applies with no errors; health endpoint returns 200; a test user can register/login and receive a valid JWT.

### Phase 1 — Physics Layer + Data Ingestion (Target: Weeks 1–2)
1. Implement all Section 5.1 calculators in `api/ml/physics/`, unit-tested against known textbook reference values
2. Implement Section 5.2 plausibility rules engine
3. Write ingestion scripts for nanoPharos, MeOx, SAPNet, Trinh, caNanoLab → clean, normalized rows in `data/processed/`
4. Load cleaned data into `material_records` / `toxicity_records` via a seed script, marked `source_type = literature_mined`, pre-approved (since this is your seed dataset, not live user contribution)
5. Build the CV/EIS simulator: generate synthetic traces via Randles-Sevcik (CV) and Randles equivalent circuit (EIS), save to `data/simulated/` in the format Module 3's parser will consume

**Validation:** physics calculators match hand-calculated reference values within floating-point tolerance; seed data loads without validation errors; simulator produces traces with recoverable known parameters when run back through the physics layer.

### Phase 2 — Module 1 (Dashboard) (Target: Weeks 2–3)
1. Backend: CRUD endpoints for material/toxicity/sensor_performance records, versioning on every edit, review endpoints (submit/approve/reject)
2. Duplicate detection on submit (DOI + material/analyte match)
3. Frontend: entry forms with Zod validation mirroring backend Pydantic rules, unit dropdowns, data table with filter/sort/export, data health panel, audit log view

**Validation:** editing a record creates a new version, not an overwrite; unreviewed records are excluded from a "trainable dataset" query; duplicate DOI submission is rejected with a clear message.

### Phase 3 — ML Training + Module 4 (Trust Layer + XAI) (Target: Weeks 3–4)
1. Build `api/ml/training/base_trainer.py`: enforces LOO-CV under 50 samples, computes SHAP, computes bootstrap confidence intervals, writes to `model_training_log`
2. Train cytotoxicity model (XGBoost + LOO-CV on nanoPharos + MeOx)
3. Train pEC50 model (XGBoost + LOO-CV on SAPNet)
4. Train Trinh mixture toxicity classifier (Random Forest, 80/20 split — only model with enough samples for a standard split)
5. Wire the trust envelope (Section 6) as the return type for every prediction endpoint
6. Frontend: shared ConfidenceBadge, SHAPWaterfallChart, PlausibilityFlag components; XAI dashboard page; model health page

**Validation:** every prediction endpoint returns a full, schema-valid PredictionEnvelope; LOO-CV is provably used for all <50-sample models (assert in tests, not just convention); re-running the same prediction against the same dataset_version_id returns identical output.

### Phase 4 — Module 2 (Design Studio) (Target: Weeks 4–5)
1. Material Explorer: search/browse endpoint + PubChem proxy integration
2. Safety card view combining local prediction + PubChem metadata
3. Retrieval-ranking engine: similarity scoring using physics-derived + raw features, ranked candidate list with trust envelopes
4. Frontend: search UI, safety card modal, ranked-candidates results view

**Validation:** ranking returns physically plausible candidates for at least 3 test specs (e.g., glucose, lead, a third analyte with known published sensors); no candidate returned with `physical_plausibility: "fail"` without a visible warning.

### Phase 5 — Module 3 (CV/LSV/EIS Analyzer) (Target: Weeks 5–7)
1. File ingestion for chosen format(s), manual column-mapping fallback UI
2. CV/LSV processing pipeline (peak detection, Randles-Sevcik, Nicholson, Cottrell)
3. EIS processing pipeline (Nyquist/Bode plotting, Randles-circuit fit via curve_fit)
4. Overlay/compare mode, calibration curve builder with confidence interval
5. Drift flag logic for repeated-electrode runs
6. Push-to-database integration into Module 1's review queue
7. Frontend: file upload, Plotly-based Nyquist/Bode/CV plots, calibration curve view

**Validation:** parser recovers known parameters from simulated traces within acceptable tolerance (define tolerance per parameter, e.g., Rct within 5%); at least one real trace (if acquired) processed successfully end-to-end; a processed result successfully appears in Module 1's review queue.

### Phase 6 — Module 5 (Access Control) (Target: Week 7, can run in parallel with Phase 4/5)
1. Role field enforcement across all mutation endpoints (`require_role()` dependency)
2. Viewer role verified to be blocked from all POST/PUT/DELETE
3. Frontend: role-aware UI (hide edit/approve controls for Viewer)

**Validation:** automated test suite confirms Viewer receives 403 on every mutation endpoint; Owner-only endpoints (review approval, user management) reject Contributor role.

### Phase 7 — Integration, Polish, Deploy (Target: Weeks 7–8)
1. End-to-end pass: seed data → dashboard → prediction → XAI view → ranking → CV/EIS upload → push back to dashboard, confirm the full loop works
2. Lighthouse pass on core pages (aim ≥85, not blocking if lower given timeline — note as known gap, not a blocker)
3. Error states: every page shows a user-readable message on API failure, never a raw exception
4. Deploy frontend to Cloudflare Pages/Vercel, backend + Postgres to Railway/Render
5. Single GitHub Action: lint + test on push
6. Write methods-section-ready documentation: what data was used, what physics equations were implemented, what validation was performed on simulated vs. real traces, LOO-CV justification

**Validation:** a cold visitor can register, browse Material Explorer, view a prediction with full trust envelope, upload a CV file, and see it processed — all in the deployed environment, not just locally.

---

## 13. Master Checklist (Condensed)

- [ ] Physics calculators unit-tested against textbook values
- [ ] LOO-CV enforced in code for all <50-sample models
- [ ] Every prediction returns the full trust envelope (value, confidence, uncertainty, SHAP, plausibility, dataset_version_id)
- [ ] "Insufficient data" is a real, visible UI state, not a disclaimer under a confident number
- [ ] Every data edit versioned, nothing overwritten in place
- [ ] Unreviewed data excluded from training by default
- [ ] Duplicate detection active at point of submission
- [ ] Viewer role blocked from all mutation endpoints (tested)
- [ ] CV/EIS parser validated against simulated ground truth with known recovery tolerance
- [ ] Retrieval-ranking never presents a single answer as certain — always ranked list with trust envelopes
- [ ] Reproducibility confirmed: same dataset_version_id + model_version → identical prediction
- [ ] No staged-but-unused datasets (UCI drift, MassBank, RRUFF, SEM, XPS) forced into v1 modules
- [ ] Deployed, publicly reachable, cold-start walkthrough works end-to-end

---

## 14. What Comes After v1 (Explicitly Deferred, Not Forgotten)

- Generative inverse-design DNN once community data volume supports it
- Full literature-mining NLP pipeline (ChemDataExtractor/OSCAR4)
- Drift/biofouling RL compensator (UCI drift dataset waiting)
- SEM/XRD/spectral modules (RRUFF, MassBank, SEM images waiting)
- Mobile app
- Institutional multi-tenant workspace hierarchy
- Regulatory/TRL/ISO/FDA/REACH tracking hub
- Robotic fabrication protocol hooks

These are not abandoned — they're the roadmap for after v1 ships and the publication is out. Keeping them out of scope now is what makes v1 achievable.

---

*Document end — SCAN Legacy Blueprint v1.0*
