from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from web3 import Web3

from server.config import settings
from server.storage import Store

logger = logging.getLogger("agora.onchain_sync")


STAKE_VAULT_ABI = [
    # views
    {
        "type": "function",
        "name": "stakeOf",
        "stateMutability": "view",
        "inputs": [{"name": "agent", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    # events
    {
        "type": "event",
        "name": "Deposited",
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "payer", "type": "address"},
            {"indexed": True, "name": "agent", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"},
        ],
    },
    {
        "type": "event",
        "name": "Withdrawn",
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "agent", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"},
        ],
    },
    {
        "type": "event",
        "name": "Slashed",
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "agent", "type": "address"},
            {"indexed": True, "name": "recipient", "type": "address"},
            {"indexed": False, "name": "requestedAmount", "type": "uint256"},
            {"indexed": False, "name": "actualAmount", "type": "uint256"},
        ],
    },
]


TREASURY_VAULT_ABI = [
    {
        "type": "event",
        "name": "DonationReceived",
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "donor", "type": "address"},
            {"indexed": True, "name": "asset", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"},
            {"indexed": True, "name": "purposeId", "type": "uint32"},
            {"indexed": False, "name": "memoHash", "type": "bytes32"},
        ],
    },
    {
        "type": "event",
        "name": "TreasurySpent",
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "executor", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": True, "name": "asset", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"},
            {"indexed": False, "name": "purposeId", "type": "uint32"},
            {"indexed": False, "name": "memoHash", "type": "bytes32"},
        ],
    },
]


def _w3(rpc_url: str) -> Web3:
    return Web3(Web3.HTTPProvider(rpc_url))


def _checksum(w3: Web3, addr: str) -> str:
    return w3.to_checksum_address(addr)


def _is_zero_address(addr: str) -> bool:
    a = (addr or "").strip().lower()
    return a == "0x0000000000000000000000000000000000000000"


def _cursor_key_prefix(prefix: str, chain_id: int, contract_addr: str) -> str:
    return f"{prefix}:{chain_id}:{contract_addr.strip().lower()}"


def _safe_latest_block(latest: int) -> int:
    conf = int(getattr(settings, "ONCHAIN_SYNC_CONFIRMATIONS", 20))
    return max(0, int(latest) - max(0, conf))


def _cursor_key(chain_id: int, contract_addr: str) -> str:
    # Back-compat: stake vault cursor key.
    return _cursor_key_prefix("stake_vault", chain_id, contract_addr)


@dataclass
class _Anchor:
    tx_hash: str
    chain_id: int
    contract_address: str
    block_number: int
    log_index: int


def sync_once(store: Store) -> dict:
    """
    Poll enabled onchain sources (best-effort) and:
    - StakeVault: update stake amount + receipt anchors; record slashing events
    - TreasuryVault: record donation events; update donor totals; auto-enable donor avatars
    - advance per-contract cursors in DB
    """
    if not (settings.RPC_URL and getattr(settings, "ONCHAIN_SYNC_ENABLED", False)):
        return {"enabled": False, "reason": "onchain sync disabled or rpc not configured"}

    w3 = _w3(settings.RPC_URL)
    chain_id = int(w3.eth.chain_id)
    latest = int(w3.eth.block_number)
    safe_latest = _safe_latest_block(latest)
    lookback = int(getattr(settings, "ONCHAIN_SYNC_LOOKBACK_BLOCKS", 2000))
    batch = int(getattr(settings, "ONCHAIN_SYNC_MAX_BLOCKS_PER_BATCH", 2000))

    out: dict = {"enabled": True, "chain_id": chain_id, "latest": latest, "safe_latest": safe_latest}

    if settings.ONCHAIN_STAKE_ENABLED and settings.STAKE_CONTRACT_ADDRESS and not _is_zero_address(settings.STAKE_CONTRACT_ADDRESS):
        out["stake"] = _sync_stake_vault_once(
            store=store,
            w3=w3,
            chain_id=chain_id,
            latest=safe_latest,
            lookback=lookback,
            batch=batch,
        )
    else:
        out["stake"] = {"enabled": False}

    if settings.TREASURY_CONTRACT_ADDRESS and not _is_zero_address(settings.TREASURY_CONTRACT_ADDRESS):
        out["treasury"] = _sync_treasury_vault_once(
            store=store,
            w3=w3,
            chain_id=chain_id,
            latest=safe_latest,
            lookback=lookback,
            batch=batch,
        )
    else:
        out["treasury"] = {"enabled": False}

    return out


def _sync_stake_vault_once(*, store: Store, w3: Web3, chain_id: int, latest: int, lookback: int, batch: int) -> dict:
    contract_addr = settings.STAKE_CONTRACT_ADDRESS
    c = w3.eth.contract(address=_checksum(w3, contract_addr), abi=STAKE_VAULT_ABI)

    key = _cursor_key_prefix("stake_vault", chain_id, contract_addr)
    from_block = store.get_onchain_cursor(key)
    if from_block is None:
        from_block = max(0, int(latest) - int(lookback))

    to_block = min(int(latest), int(from_block) + max(1, int(batch)) - 1)
    if to_block < from_block:
        return {"enabled": True, "contract": contract_addr, "from_block": from_block, "to_block": to_block, "updated": 0}

    touched: dict[str, _Anchor] = {}
    slashes_recorded = 0

    for ev in c.events.Deposited().get_logs(from_block=from_block, to_block=to_block):
        agent = str(ev["args"]["agent"]).lower()
        touched[agent] = _Anchor(
            tx_hash=ev["transactionHash"].hex(),
            chain_id=chain_id,
            contract_address=contract_addr.lower(),
            block_number=int(ev["blockNumber"]),
            log_index=int(ev["logIndex"]),
        )

    for ev in c.events.Withdrawn().get_logs(from_block=from_block, to_block=to_block):
        agent = str(ev["args"]["agent"]).lower()
        touched[agent] = _Anchor(
            tx_hash=ev["transactionHash"].hex(),
            chain_id=chain_id,
            contract_address=contract_addr.lower(),
            block_number=int(ev["blockNumber"]),
            log_index=int(ev["logIndex"]),
        )

    for ev in c.events.Slashed().get_logs(from_block=from_block, to_block=to_block):
        agent = str(ev["args"]["agent"]).lower()
        recipient = str(ev["args"]["recipient"]).lower()
        actual_raw = int(ev["args"]["actualAmount"])
        tx_hash = ev["transactionHash"].hex()
        log_index = int(ev["logIndex"])
        block_number = int(ev["blockNumber"])

        touched[agent] = _Anchor(
            tx_hash=tx_hash,
            chain_id=chain_id,
            contract_address=contract_addr.lower(),
            block_number=block_number,
            log_index=log_index,
        )

        event_id = f"{chain_id}:{tx_hash}:{log_index}"
        store.record_slash(
            event={
                "id": event_id,
                "agent_address": agent,
                "amount_usdc": actual_raw / 1_000_000,
                "recipient_address": recipient,
                "job_id": None,
                "tx_hash": tx_hash,
                "chain_id": chain_id,
                "contract_address": contract_addr.lower(),
                "block_number": block_number,
                "log_index": log_index,
                "created_at": None,
            }
        )
        slashes_recorded += 1

    updated = 0
    for agent, a in touched.items():
        try:
            raw = int(c.functions.stakeOf(_checksum(w3, agent)).call())
            store.set_stake(
                agent,
                raw / 1_000_000,
                stake_tx_hash=a.tx_hash,
                stake_chain_id=a.chain_id,
                stake_contract_address=a.contract_address,
                stake_block_number=a.block_number,
                stake_log_index=a.log_index,
            )
            updated += 1
        except Exception:
            logger.exception("failed updating stake for agent=%s", agent)

    store.set_onchain_cursor(key, to_block + 1)
    return {
        "enabled": True,
        "contract": contract_addr,
        "from_block": from_block,
        "to_block": to_block,
        "touched_agents": len(touched),
        "stake_updates": updated,
        "slashes_recorded": slashes_recorded,
        "next_from_block": to_block + 1,
    }


def _sync_treasury_vault_once(*, store: Store, w3: Web3, chain_id: int, latest: int, lookback: int, batch: int) -> dict:
    contract_addr = settings.TREASURY_CONTRACT_ADDRESS
    c = w3.eth.contract(address=_checksum(w3, contract_addr), abi=TREASURY_VAULT_ABI)

    key = _cursor_key_prefix("treasury_vault", chain_id, contract_addr)
    from_block = store.get_onchain_cursor(key)
    if from_block is None:
        from_block = max(0, int(latest) - int(lookback))

    to_block = min(int(latest), int(from_block) + max(1, int(batch)) - 1)
    if to_block < from_block:
        return {"enabled": True, "contract": contract_addr, "from_block": from_block, "to_block": to_block, "donations_recorded": 0}

    donations_seen = 0
    donations_recorded = 0

    usdc_addr = (settings.USDC_ADDRESS or "").strip().lower()
    eth_usd_rate = float(getattr(settings, "ETH_USD_RATE", 2500.0))

    for ev in c.events.DonationReceived().get_logs(from_block=from_block, to_block=to_block):
        donations_seen += 1
        donor = str(ev["args"]["donor"]).lower()
        asset = str(ev["args"]["asset"]).lower()
        amount_raw = int(ev["args"]["amount"])
        purpose_id = int(ev["args"].get("purposeId", 0))
        memo_hash = ev["args"].get("memoHash")
        memo_hex = memo_hash.hex() if hasattr(memo_hash, "hex") else str(memo_hash)

        tx_hash = ev["transactionHash"].hex()
        log_index = int(ev["logIndex"])
        block_number = int(ev["blockNumber"])

        amount_usd: float | None = None
        if asset == "0x0000000000000000000000000000000000000000":
            amount_usd = (amount_raw / 1e18) * eth_usd_rate
        elif usdc_addr and asset == usdc_addr:
            amount_usd = amount_raw / 1_000_000

        event_id = f"{chain_id}:{tx_hash}:{log_index}"
        try:
            store.record_donation_event(
                event={
                    "id": event_id,
                    "donor_address": donor,
                    "asset_address": asset,
                    "amount_raw": amount_raw,
                    "amount_usd": amount_usd,
                    "purpose_id": purpose_id,
                    "memo_hash": memo_hex,
                    "tx_hash": tx_hash,
                    "chain_id": chain_id,
                    "contract_address": contract_addr.lower(),
                    "block_number": block_number,
                    "log_index": log_index,
                    "created_at": None,
                }
            )
            donations_recorded += 1
        except Exception:
            logger.exception("failed recording donation event_id=%s", event_id)

    store.set_onchain_cursor(key, to_block + 1)
    return {
        "enabled": True,
        "contract": contract_addr,
        "from_block": from_block,
        "to_block": to_block,
        "donations_seen": donations_seen,
        "donations_recorded": donations_recorded,
        "next_from_block": to_block + 1,
    }


def run_loop(store: Store) -> None:
    """
    Best-effort background loop. Safe to run in a daemon thread.
    """
    poll = int(getattr(settings, "ONCHAIN_SYNC_POLL_SECONDS", 5))
    while True:
        try:
            if getattr(settings, "ONCHAIN_SYNC_ENABLED", False):
                sync_once(store)
        except Exception:
            logger.exception("onchain sync loop error")
        time.sleep(max(1, poll))

