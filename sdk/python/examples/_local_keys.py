from __future__ import annotations

import json
import os
import secrets
from pathlib import Path


def load_or_create_private_key() -> str:
    """
    Returns an EOA private key for signing.

    Priority:
    1) AGORA_PRIVATE_KEY env var
    2) ~/.config/agora/credentials.json (private_key)
    3) generate once + persist to ~/.config/agora/credentials.json

    Security note:
    - The stored key should be treated as a secret (chmod 600 best-effort).
    - In production, prefer a proper secret manager over a plaintext file.
    """
    env_key = (os.getenv("AGORA_PRIVATE_KEY") or "").strip()
    if env_key:
        return env_key

    cred_path = Path.home() / ".config" / "agora" / "credentials.json"
    if cred_path.exists():
        try:
            data = json.loads(cred_path.read_text(encoding="utf-8"))
            pk = str(data.get("private_key") or "").strip()
            if pk:
                return pk
        except Exception:
            pass

    # Create & persist
    pk = "0x" + secrets.token_hex(32)
    cred_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"private_key": pk}
    cred_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    try:
        # best-effort POSIX permissions
        os.chmod(cred_path, 0o600)
    except Exception:
        pass
    return pk

