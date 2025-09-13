Agent Guidelines for This Repo

Purpose
- This repository implements a local webcam presence and gesture detection service. Recent work adds a presence gating pipeline (pHash + SSIM + hysteresis) to reduce false positives in visually busy scenes.

Workflow (TDD First)
- Always use strict TDD: red → green → refactor.
- Add focused tests before code; keep each test file under ~300 lines where possible.
- Prefer small, composable modules over large files; make surgical changes.
- Do not change environment variables or unrelated configs to make tests pass.
- After green, refactor for clarity, separation of concerns, and robustness without changing behavior.

Planning and Tooling
- Use the plan tool to track steps when a task spans multiple actions.
- Before running terminal commands, post a brief preamble describing the action.
- Prefer ripgrep (`rg`) for repo search; read files in chunks ≤250 lines when needed.
- Use `apply_patch` for all edits. Do not add licenses or copyright headers.

Branching and Commits
- Work on feature branches named `feature/<short-description>` (e.g., `feature/webcam-presence-gating`).
- Use clear commit messages (Conventional Commits style preferred). Keep changes minimal and scoped.
- Do not commit images, large binaries, or secrets. Images used for debugging must not be stored in Git.

Code Conventions
- Follow existing style and structure. Avoid refactoring unrelated code.
- Keep modules small and focused. Avoid one-letter variable names.
- Avoid adding heavy dependencies. Image ops should use existing NumPy/OpenCV.
- Do not write inline code comments unless explicitly requested.

Presence Gating Components
- Image similarity utilities: `src/processing/image_similarity.py`
  - `compute_phash(img)`: 64‑bit pHash using DCT on 32×32 grayscale.
  - `phash_distance(h1,h2)`: Hamming distance.
  - `edge_ssim(img1,img2)`: simplified global SSIM on Sobel magnitude.
- Reference manager: `src/processing/reference_manager.py`
  - Maintains small in‑memory grayscale, downscaled references and their pHashes.
  - Simple FIFO eviction (max size configurable).
- Presence gate: `src/processing/presence_gate.py`
  - pHash fast gate → edge‑SSIM confirm; enter/exit hysteresis and cooldown.
  - Auto‑captures a reference after stable “no‑human” period (in‑memory only).
- Service integration: `webcam_service.py`
  - When `gating.enabled` is true, uses gated presence for HTTP/SSE and gesture gating.

Configuration
- Main detection config: `config/detection_config.yaml`
- Gating keys (enabled by default):
  - `gating.enabled: true`
  - `gating.phash_threshold_same: 10`
  - `gating.ssim_threshold_same: 0.90`
  - `gating.hysteresis.enter_k: 3`, `gating.hysteresis.exit_l: 5`
  - `gating.cooldown_ms: 1000`
  - `refs.capture_stable_seconds: 5`, `refs.max_per_bucket: 3` (in v1, global max)

Running and Testing
- Run unit tests for gating: `pytest -q tests/test_presence_gating.py`
- Start service: `python webcam_service.py`
  - Presence API: `GET /presence`, `GET /presence/simple` (port 8767)
  - Presence SSE: `GET /events/presence/{client_id}` (port 8764)
- Let the camera view remain empty for ~5s on startup to auto‑capture references.

Performance & Privacy
- Gating runs lightweight ops; consider evaluating every N frames if CPU is constrained (future enhancement).
- Do not persist frames or references to Git. Any future on‑disk refs must live under a temp dir (e.g., `/tmp/ziggy-webcam/refs`) and be gitignored.
- Snapshot/debug endpoints must be guarded by config and are optional.

Future Phases (not yet implemented)
- Luminance‑derived “lighting buckets” for references.
- Tuning endpoints: reset references, metrics.
- Frame‑rate throttled gating evaluation.

Scope Discipline
- Only touch files required for the task. Do not change unrelated modules or external APIs unless necessary.
- If existing tests fail due to unrelated issues, surface them but do not fix unless asked.

