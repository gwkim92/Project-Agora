from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running from repo root without PYTHONPATH tweaks.
_SDK_ROOT = Path(__file__).resolve().parents[1]
if str(_SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(_SDK_ROOT))

from agora_sdk.client import AgoraClient  # noqa: E402
from _local_keys import load_or_create_private_key  # noqa: E402


def main() -> None:
    # Prefer the deployed API by default. Override with AGORA_API_BASE for local testing.
    base_url = os.environ.get("AGORA_API_BASE", "https://api.project-agora.im")
    private_key = load_or_create_private_key()

    c = AgoraClient(base_url=base_url, private_key=private_key)
    token = c.authenticate()
    print("address:", c.address)
    print("access_token:", token[:16] + "…")


if __name__ == "__main__":
    main()

