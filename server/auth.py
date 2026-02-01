from __future__ import annotations

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from server.config import settings


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


def build_admin_message_to_sign(*, address: str, nonce: str, base_url: str) -> str:
    addr = normalize_address(address)
    return (
        "Project Agora Admin Access\n"
        f"Base URL: {base_url}\n"
        f"Address: {addr}\n"
        f"Nonce: {nonce}\n"
        "Statement: Sign to access operator/admin actions.\n"
    )


def verify_signature(*, address: str, message: str, signature: str) -> bool:
    addr = normalize_address(address)
    # 1) EOA signature (personal_sign / EIP-191)
    try:
        recovered = Account.recover_message(encode_defunct(text=message), signature=signature)
        if normalize_address(recovered) == addr:
            return True
    except Exception:
        pass

    # 2) Contract wallet / multisig (EIP-1271) - optional
    # Many multisigs (e.g. Safe) are contract accounts and cannot "sign" like EOAs.
    # They validate signatures on-chain via isValidSignature.
    if not settings.AUTH_EIP1271_ENABLED:
        return False
    if not settings.RPC_URL:
        return False

    try:
        w3 = Web3(Web3.HTTPProvider(settings.RPC_URL))
        checksum = w3.to_checksum_address(addr)
        code = w3.eth.get_code(checksum)
        if not code or code == b"\x00":
            return False

        # EIP-1271: isValidSignature(bytes32,bytes) => bytes4 magicValue
        # magicValue: 0x1626ba7e
        #
        # For "personal_sign"/EIP-191 style signatures, eth-account signs the EIP-191 payload:
        #   keccak256(0x19 || version || header || body)
        # where encode_defunct returns a SignableMessage(version, header, body).
        m = encode_defunct(text=message)
        msg_hash = w3.keccak(b"\x19" + m.version + m.header + m.body)
        abi = [
            {
                "type": "function",
                "name": "isValidSignature",
                "stateMutability": "view",
                "inputs": [{"name": "hash", "type": "bytes32"}, {"name": "signature", "type": "bytes"}],
                "outputs": [{"name": "magicValue", "type": "bytes4"}],
            }
        ]
        c = w3.eth.contract(address=checksum, abi=abi)
        magic: bytes = c.functions.isValidSignature(msg_hash, bytes.fromhex(signature.removeprefix("0x"))).call()
        return magic == bytes.fromhex("1626ba7e")
    except Exception:
        return False

