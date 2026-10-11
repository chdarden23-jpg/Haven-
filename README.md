# ANEIRA V3 — Unified Survivor Recovery Application

This source package is the **independent integrated V3 application**. It is not deployed and has no V2 activity engines, V2 activity datasets, or rejected V2 questionnaire imports. The original source text for retained content is not modified.

## Verified retained inventories

- **66 original V3 assessment questions** covering **10 recovery domains**, plus separate support and preference items, all preserved verbatim in `data/questions.json`.
- **45 V3 therapeutic exercises**, unique IDs, full original instructions and evidence annotations, in `data/exercise_master.json`.
- **41 V3 structured journals**, unique IDs, all original prompts and follow-up questions, in `data/journaling_library.json`.
- **30 V3 educational chapters**, full source content, in `data/chapters.json`.
- Approved user-provided reference image in `static/approved_homepage_user.jpeg`; secondary imagery from the supplied homepage archive in `static/`.
- Python V3 assessment interpretation source in `aneira_assessment/` plus unified orchestration in `intelligence.py`.

See `docs/SOURCE_MANIFEST.json` for paths, hashes and legacy exclusions. The source ZIP labeled `aneira_v2/` is a mixed-history container. **Only its V3-approved chapter database and visual assets were imported**. Its application engines, questionnaire bank and activities were **not** imported. The V3 assessment source likewise contained an inherited V2 activity dependency which was explicitly excluded.

## Start locally

Python 3.11+ recommended. From the application directory:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Keep the printed Fernet key in a **persistent environment secret** as `ANEIRA_ENCRYPTION_KEY`; never place the actual value in the repository. Set `ANEIRA_DATABASE` to a persistent writable path. To test over plain HTTP on `localhost`, set `ANEIRA_INSECURE_LOCAL=1` only for local development; omit this in production. Then:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000`. For deployment, serve behind HTTPS with TLS termination at a correctly configured reverse proxy, set `ANEIRA_PUBLIC_URL`, use persistent encrypted backups, and configure production mail below.

## Password-reset email

Set `ANEIRA_SMTP_HOST`, `ANEIRA_SMTP_PORT` (default 465), `ANEIRA_SMTP_USER`, `ANEIRA_SMTP_PASSWORD`, `ANEIRA_SMTP_FROM`, and `ANEIRA_PUBLIC_URL`. Forgot-password requests do not disclose whether an email is registered. Reset tokens expire in 15 minutes, are single-use and are stored hashed. Without SMTP credentials, the reset *endpoint* can accept a request but cannot deliver an email; the system does not pretend the email was sent. For robust commercial delivery, add an email queue and throttling.

## Privacy and security

- Passwords: salted scrypt; sessions: random HttpOnly SameSite=Strict cookies with Secure flag in production; database stores token hashes only.
- Records: SQLite relational owner isolation with encrypted Fernet (AES-128-CBC + HMAC) envelopes, including assessments, journals, activity history, cognitive choices and affirmations. This is **encrypted-at-rest record content**, not SQLCipher full-database encryption. Password reset hashes and account emails are not Fernet-encrypted.
- Data: export/delete routes and account deletion. App does not explicitly log assessment content. App disables OpenAPI documentation routes. Reverse proxy and platform logs still require privacy configuration.
- Server has a `ANEIRA_DEMO_MODE=1` setting rejecting mutations to prevent saving demo-sensitive input. Demo content and authentication are intentionally nonpersistent in this mode; it is not a functioning temporary demo account.
- Environment secrets are mandatory for startup. Do not use development HTTP cookies for production.

**Production hardening outstanding:** SMTP setup/delivery verification, rate limits and brute-force protection, email verification/MFA, per-user key management and rotation, operational logging review, secret backup policy, deletion of backups, penetration testing, legal/privacy review, reverse-proxy HTTPS verification, and professional clinical safety review. Do not use this application to store real survivor disclosures until these production controls have been independently validated.

## Assessment and recommendation behavior

Original V3 scoring is descriptive and not a validated clinical severity instrument. `aneira_assessment/engine.py` validates the exact question-specific choices, preserves skips as missing, and prioritizes selected goals and reported interference. `interpretation.py` creates question-specific report paragraphs, incorporates relevant identified relationships and distinguishes current practical threats from reported symptoms. `intelligence.py` links profiles to the original exercise/journal IDs and actual chapter slugs, ranks recommendations and suggests affirmation content. It also implements ten V3-only cognitive scenarios with multiple immediate choice-specific explanations, optional follow-up, and recognition history.

The frontend includes 10 functional navigation sections: home, education, assessment, results, studio, journals, reality recognition, affirmations, progress within dashboard, and private dashboard. The frontend uses the approved image as a visual design reference, not a pixel-exact reproduction.

## Automated QA

Run:

```bash
pytest -q tests/test_full_v3.py
node --check static/app.js  # optional Node.js syntax check
```

See `docs/QA_VERIFICATION_MATRIX.md` and `docs/TEST_RESULTS.txt`. **40 automated Python tests passed** when packaged. API and Python integration tests were executed with FastAPI TestClient. Browser rendering/visual testing could not be completed because Chromium was blocked by environment policy. A deployed browser/device acceptance test remains mandatory.

## Source folders

- `main.py`: FastAPI routes, auth, account-scoped APIs, sensitive data management.
- `storage.py`: encryption, password/session management, user-scoped persistence.
- `intelligence.py`: V3-only recovery orchestration and choice-specific interaction.
- `aneira_assessment/`: retained original assessment engine and interpretation components; external legacy recommendation bridge omitted.
- `data/`: original V3 catalogs and scientific metadata.
- `static/`: responsive frontend and authorized images.
- `docs/`: provenance manifest, original scientific report, original research document, QA and acceptance status.
- `tests/`: automated tests.

No source archives are separately required at runtime.
