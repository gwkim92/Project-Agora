from __future__ import annotations

from eth_account import Account
from eth_account.messages import encode_defunct


def normalize_address(address: str) -> str:
    return address.strip().lower()


def build_message_to_sign(*, address: str, nonce: str, base_url: str) -> str:
    # EIP-4361 (SIWE)까지 가기 전의 최소 메시지.
    # (Phase 2+) 필요 시 SIWE로 교체 가능하되, 인터페이스는 유지.
    addr = normalize_address(address)
    return (
        "Project Agora Authentication\n"
        f"Base URL: {base_url}\n"
        f"Address: {addr}\n"
        f"Nonce: {nonce}\n"
        "Statement: Sign to authenticate as this agent.\n"
    )


def verify_signature(*, address: str, message: str, signature: str) -> bool:
    addr = normalize_address(address)
    recovered = Account.recover_message(encode_defunct(text=message), signature=signature)
    return normalize_address(recovered) == addr

