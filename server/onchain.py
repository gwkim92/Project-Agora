from __future__ import annotations

from functools import lru_cache

from web3 import Web3


STAKE_VAULT_ABI = [
    {
        "type": "function",
        "name": "stakeOf",
        "stateMutability": "view",
        "inputs": [{"name": "agent", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    }
]


def _to_checksum(w3: Web3, address: str) -> str:
    return w3.to_checksum_address(address)


@lru_cache(maxsize=4)
def _w3(rpc_url: str) -> Web3:
    return Web3(Web3.HTTPProvider(rpc_url))


def get_stake_amount_usdc(*, rpc_url: str, stake_contract: str, agent_address: str) -> float:
    """
    Returns staked amount in "USDC units" assuming 6 decimals in the staking vault.
    (We keep this simple for Phase 1. If the vault supports arbitrary ERC20, extend this.)
    """
    w3 = _w3(rpc_url)
    c = w3.eth.contract(address=_to_checksum(w3, stake_contract), abi=STAKE_VAULT_ABI)
    raw: int = c.functions.stakeOf(_to_checksum(w3, agent_address)).call()
    return raw / 1_000_000  # USDC: 6 decimals

