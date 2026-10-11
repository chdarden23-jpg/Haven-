# ANEIRA V3 — Integration Verification Matrix

**Status:** Python backend integrated and exercised, 40/40 tests pass. Browser rendering and fully clickable visual acceptance testing are **not verified** because the container browser returned `ERR_BLOCKED_BY_ADMINISTRATOR` for local HTTP and file pages.

| # | User acceptance requirement | Implementation | Evidence / verification |
|---|---|---|---|
| 1 | No rejected V2 activity files | Explicit exclusion | Manifest + `test_03` PASS |
| 2 | Three authorized source packages accounted for | Source SHA256 manifest | `test_01`, `test_38` PASS |
| 3 | All 66 questions preserved | `data/questions.json` | `test_01`, `test_38` PASS |
| 4 | Ten recovery domains | `data/domains.json`, V3 engine | `test_01`, `test_11` PASS |
| 5 | All 45 V3 exercises | `data/exercise_master.json` | `test_01`, `test_02`, `test_38` PASS |
| 6 | All 41 V3 journals | `data/journaling_library.json` | `test_01`, `test_02`, `test_38` PASS |
| 7 | All 30 chapters | `data/chapters.json` | `test_01`, `test_02`, `test_38` PASS |
| 8 | User-approved image | `static/approved_homepage_user.jpeg` | `test_04` PASS |
| 9 | Registration/login | `storage.py`, `main.py` | `test_25`, `test_26` PASS |
| 10 | Password reset | `storage.py`, `main.py` | `test_34` PASS for reset-token endpoint; SMTP delivery NOT VERIFIED/configuration dependent |
| 11 | Account isolation | SQL user owner filter | `test_26` PASS |
| 12 | Response types | V3 `validate_answers` | `test_05`, `test_06` PASS |
| 13 | Missing values unknown | V3 engine | `test_08` PASS |
| 14 | Low confidence reverse-coded | V3 `disruption()` | `test_09` PASS |
| 15 | Serious disclosure support routing | V3 `safety_routing()` | `test_12` PASS |
| 16 | Distinct survivor reports | V3 `interpret()` | `test_15`, `test_33` PASS |
| 17 | Exercise IDs genuinely present | V3 orchestration | `test_17`, `test_32` PASS |
| 18 | Journal IDs genuinely present | V3 orchestration | `test_18`, `test_19`, `test_32` PASS |
| 19 | Immediate answer-specific cognitive explanations | `cognitive_reply()` | `test_21`, `test_30` PASS |
| 20 | Adaptive next scenario | `cognitive_reply()` + saved history | `test_22` PASS |
| 21 | Distinct affirmation follow-ups | `FOLLOWUPS`, API | `test_23`, `test_31` PASS |
| 22 | Journal CRUD | Encrypted `records` | `test_28` PASS |
| 23 | Progress persists across logouts | Encrypted storage | `test_25`, `test_29` PASS |
| 24 | Reassessment updates priorities | V3 engine | `test_40` PASS; historical change engine test `test_16` PASS |
| 25 | All frontend routes/buttons | HTML/CSS/JS frontend | UI implemented, JS syntax checked; **full browser click-path NOT VERIFIED** |
| 26 | Desktop/mobile browser visual fidelity | Responsive CSS breakpoints | CSS present, **rendered-browser checks BLOCKED**; not pixel-verified |
| 27 | Backend starts | Uvicorn startup + GET `/health` | PASS: returned status ok, 66/45/41/30 counts |
| 28 | Dependencies/assets in ZIP | `requirements.txt`, static/, tests/, docs/ | Source ZIP validated for integrity |

Additional checks: encrypted record payloads (`test_27` PASS), no private journal body in stdout (`test_39` PASS), account deletion (`test_35` PASS), consent enforcement (`test_36` PASS), chapter slug integrity (`test_20` PASS), catalog preservation hash matching (`test_38` PASS), account export (`test_26` PASS).

## Remaining acceptance blockers

1. Browser/UI automated click-path verification and true desktop/tablet/mobile layout inspection were not completed due to environment policy. **Not a tested browser release.**
2. Password reset **email transmission** requires externally configured SMTP and was not end-to-end verified.
3. HTTPS/TLS operates in the deployment proxy, not standalone Uvicorn; production HTTPS verification is outstanding.
4. This is a new standalone integrated web app; it has not been deployed or tested on the user's eventual hosting platform.
5. Static interpretation rules and ANEIRA-developed questions need clinical content QA before use with real survivors.
6. Full production security requirements (MFA, email verification, rate limits, infrastructure security, incident response) are not all complete.
7. Recovery activities execute as interactive checklists/reflections; source-specific activity UI widgets beyond the original step instructions are not implemented. Full clinical-grade interactive therapeutic adaptation remains outstanding.

**No claims of passed browser tests, delivered reset emails, or full security compliance are made.**
