# ANEIRA V3 Render deployment

This archive is deliberately **flat**: `main.py`, `intelligence.py`, `storage.py`, `requirements.txt`, and `aneira_assessment/` must all be in the **GitHub repository root**. Upload the *contents* of this archive, not the archive itself.

Render settings: Root Directory **blank**, Build Command `pip install -r requirements.txt`, Start Command `uvicorn main:app --host 0.0.0.0 --port $PORT`.

Environment variable `ANEIRA_ENCRYPTION_KEY`: generate a stable Fernet key with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and save it privately. Do not place the secret in GitHub or rotate it after saving encrypted records without a migration.

`/health` is a non-sensitive readiness endpoint. This app uses SQLite and local runtime storage, which is ephemeral on typical Render services unless persistent storage is configured. **Do not use this deployment for real survivor records until durable protected storage, access control, privacy and security reviews are complete.**
