from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass

import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3


@dataclass
class CompileResult:
    abi: list[dict]
    bytecode: str


def _sh(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True)


def compile_contract() -> CompileResult:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(repo_root, "contracts", "MockEIP1271Wallet.sol")
    # Use solc via docker for deterministic compilation without extra local deps.
    out = _sh(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{repo_root}:/src",
            "ethereum/solc:0.8.20",
            "--optimize",
            "--combined-json",
            "abi,bin",
            f"/src/contracts/MockEIP1271Wallet.sol",
        ]
    )
    data = json.loads(out)
    contracts = data["contracts"]
    # solc keys vary by invocation path (e.g. "/src/contracts/..." vs "contracts/...")
    # Find the entry for MockEIP1271Wallet deterministically.
    key = None
    for k in contracts.keys():
        if k.endswith(":MockEIP1271Wallet") and "MockEIP1271Wallet.sol" in k:
            key = k
            break
    if key is None:
        # fallback: pick any contract with the right name
        for k in contracts.keys():
            if k.endswith(":MockEIP1271Wallet"):
                key = k
                break
    if key is None:
        raise RuntimeError(f"compile output missing MockEIP1271Wallet; keys={list(contracts.keys())[:5]}...")

    abi_raw = contracts[key]["abi"]
    abi = json.loads(abi_raw) if isinstance(abi_raw, str) else abi_raw
    bytecode = "0x" + contracts[key]["bin"]
    return CompileResult(abi=abi, bytecode=bytecode)


def wait_http(url: str, timeout_s: float = 10.0) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            r = requests.get(url, timeout=1.0)
            if r.status_code < 500:
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"timeout waiting for {url}")


def main() -> None:
    base_url = os.getenv("AGORA_BASE_URL", "http://localhost:8000")
    rpc_url = os.getenv("AGORA_RPC_URL", "http://localhost:18545")

    print("base_url:", base_url)
    print("rpc_url:", rpc_url)

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise SystemExit("RPC not reachable. Start anvil first.")

    compile_res = compile_contract()

    # Owner key (this is the signer used by the contract wallet)
    owner_acct = Account.create()
    owner_addr = owner_acct.address
    print("mock wallet owner:", owner_addr)

    # Deploy the mock EIP-1271 wallet from an unlocked anvil account
    deployer = w3.eth.accounts[0]
    w3.eth.default_account = deployer

    contract = w3.eth.contract(abi=compile_res.abi, bytecode=compile_res.bytecode)
    tx_hash = contract.constructor(owner_addr).transact()
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    wallet_addr = receipt.contractAddress
    print("deployed MockEIP1271Wallet:", wallet_addr)

    # Agora auth flow using contract wallet address
    wait_http(f"{base_url}/healthz", timeout_s=10.0)

    challenge = requests.post(
        f"{base_url}/api/v1/agents/auth/challenge",
        json={"address": wallet_addr},
        timeout=10.0,
    )
    challenge.raise_for_status()
    message = challenge.json()["message_to_sign"]

    sig = Account.sign_message(encode_defunct(text=message), owner_acct.key).signature.hex()

    # Sanity-check EIP-1271 on-chain result directly before hitting the API verify.
    wallet = w3.eth.contract(address=wallet_addr, abi=compile_res.abi)
    m = encode_defunct(text=message)
    msg_hash = w3.keccak(b"\x19" + m.version + m.header + m.body)
    magic = wallet.functions.isValidSignature(msg_hash, bytes.fromhex(sig.removeprefix("0x"))).call()
    print("onchain isValidSignature:", Web3.to_hex(magic))

    verify = requests.post(
        f"{base_url}/api/v1/agents/auth/verify",
        json={"address": wallet_addr, "signature": sig},
        timeout=10.0,
    )
    if verify.status_code != 200:
        print("verify failed:", verify.status_code, verify.text[:500])
    verify.raise_for_status()
    token = verify.json()["access_token"]
    print("auth ok, token:", token[:12] + "…")

    # Read reputation for contract wallet address (should exist)
    rep = requests.get(f"{base_url}/api/v1/reputation/{wallet_addr}", timeout=10.0)
    rep.raise_for_status()
    print("rep:", rep.json())


if __name__ == "__main__":
    main()

