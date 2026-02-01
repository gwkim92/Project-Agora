"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { connectWallet, getActiveProvider, loadWalletAuth, saveWalletAuth } from "@/lib/walletAuth";
import type { TreasuryInfo } from "@/lib/types";
import { encodeFunctionData, isAddress, keccak256, parseUnits, stringToHex } from "viem";

const VAULT_ABI = [
  {
    type: "function",
    name: "donateEth",
    stateMutability: "payable",
    inputs: [
      { name: "purposeId", type: "uint32" },
      { name: "memoHash", type: "bytes32" },
    ],
    outputs: [],
  },
  {
    type: "function",
    name: "donateUsdc",
    stateMutability: "nonpayable",
    inputs: [
      { name: "amount", type: "uint256" },
      { name: "purposeId", type: "uint32" },
      { name: "memoHash", type: "bytes32" },
    ],
    outputs: [],
  },
] as const;

const ERC20_ABI = [
  {
    type: "function",
    name: "approve",
    stateMutability: "nonpayable",
    inputs: [
      { name: "spender", type: "address" },
      { name: "amount", type: "uint256" },
    ],
    outputs: [{ name: "", type: "bool" }],
  },
] as const;

type Asset = "ETH" | "USDC";

function isZeroAddress(addr: string): boolean {
  return addr.toLowerCase() === "0x0000000000000000000000000000000000000000";
}

function short(addr: string) {
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}

function explorerBaseForChainId(chainId: number): string | null {
  if (chainId === 8453) return "https://basescan.org";
  if (chainId === 84532) return "https://sepolia.basescan.org";
  return null;
}

function memoToHash(memo: string): `0x${string}` {
  const trimmed = memo.trim();
  if (!trimmed) return "0x0000000000000000000000000000000000000000000000000000000000000000";
  return keccak256(stringToHex(trimmed));
}

function asHexAddress(addr: string, label: string): `0x${string}` {
  if (!isAddress(addr)) throw new Error(`Invalid address for ${label}`);
  return addr as `0x${string}`;
}

export function DonateWidget({
  treasury,
  purposes,
}: {
  treasury: TreasuryInfo | null;
  purposes: Array<{ id: number; label: string }>;
}) {
  const [asset, setAsset] = useState<Asset>("ETH");
  const [purposeId, setPurposeId] = useState<number>(purposes[0]?.id ?? 1);
  const [amount, setAmount] = useState<string>("");
  const [memo, setMemo] = useState<string>("");
  // Important: avoid hydration mismatch by making the initial render identical on server & client.
  // We'll load any cached wallet address only after mount.
  const [mounted, setMounted] = useState(false);
  const [address, setAddress] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [txHash, setTxHash] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    setMounted(true);
    try {
      const s = loadWalletAuth();
      setAddress(s.address ?? null);
    } catch {
      setAddress(null);
    }
  }, []);

  const disabledReason = useMemo(() => {
    if (!treasury) return "Server config not loaded.";
    if (!isAddress(treasury.contract_address)) return "Invalid treasury contract address.";
    if (isZeroAddress(treasury.contract_address)) return "Treasury is not deployed yet (zero-address).";
    if (asset === "USDC") {
      if (!isAddress(treasury.usdc_address)) return "Invalid USDC address.";
      if (isZeroAddress(treasury.usdc_address)) return "USDC address is not configured.";
    }
    return null;
  }, [asset, treasury]);

  async function ensureWalletConnected(): Promise<string> {
    const s = loadWalletAuth();
    if (s.address) return s.address;
    const addr = await connectWallet();
    saveWalletAuth({ address: addr, connector: s.connector ?? "injected" });
    return addr;
  }

  async function sendTx(tx: { from: string; to: string; data?: `0x${string}`; value?: `0x${string}` }) {
    const provider = getActiveProvider();
    if (!provider?.request) throw new Error("No wallet provider available");
    const h = (await provider.request({ method: "eth_sendTransaction", params: [tx] })) as string;
    return h;
  }

  async function onDonate() {
    setStatus(null);
    setTxHash(null);

    const reason = disabledReason;
    if (reason) {
      setStatus(reason);
      return;
    }

    if (!amount.trim()) {
      setStatus("Enter an amount.");
      return;
    }

    if (!treasury) return;

    setIsBusy(true);
    try {
      const from = await ensureWalletConnected();
      setAddress(from);

      const memoHash = memoToHash(memo);
      const vaultAddr = asHexAddress(treasury.contract_address, "treasury.contract_address");

      if (asset === "ETH") {
        setStatus("Preparing ETH donation…");
        const valueWei = parseUnits(amount, 18);
        const data = encodeFunctionData({
          abi: VAULT_ABI,
          functionName: "donateEth",
          args: [purposeId, memoHash],
        });
        const h = await sendTx({
          from,
          to: vaultAddr,
          data,
          value: `0x${valueWei.toString(16)}`,
        });
        setTxHash(h);
        setStatus("Transaction sent.");
        return;
      }

      // USDC path: approve -> donateUsdc
      const usdcAddr = asHexAddress(treasury.usdc_address, "treasury.usdc_address");
      setStatus("Preparing USDC approval…");
      const usdcAmount = parseUnits(amount, 6);
      const approveData = encodeFunctionData({
        abi: ERC20_ABI,
        functionName: "approve",
        args: [vaultAddr, usdcAmount],
      });
      const approveHash = await sendTx({
        from,
        to: usdcAddr,
        data: approveData,
      });
      setTxHash(approveHash);
      setStatus("Approval sent. Now sending donation…");

      const donateData = encodeFunctionData({
        abi: VAULT_ABI,
        functionName: "donateUsdc",
        args: [usdcAmount, purposeId, memoHash],
      });
      const donateHash = await sendTx({
        from,
        to: vaultAddr,
        data: donateData,
      });
      setTxHash(donateHash);
      setStatus("Donation transaction sent.");
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Donation failed");
    } finally {
      setIsBusy(false);
    }
  }

  const explorer = treasury ? explorerBaseForChainId(treasury.chain_id) : null;
  const txUrl = explorer && txHash ? `${explorer}/tx/${txHash}` : null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="text-sm text-slate-300">
          Wallet:{" "}
          {mounted && address ? (
            <span className="font-mono text-slate-200">{short(address)}</span>
          ) : (
            <span className="text-slate-500">Not connected</span>
          )}
        </div>
        <div className="text-xs text-slate-500">
          Gas policy: <span className="text-slate-300">no sponsorship</span>
        </div>
      </div>

      <div className="grid md:grid-cols-4 gap-3">
        <div className="md:col-span-1">
          <div className="text-xs text-slate-500 mb-1">Asset</div>
          <div className="flex gap-2" role="radiogroup" aria-label="Asset">
            <Button
              variant={asset === "ETH" ? "default" : "outline"}
              className="w-full font-sans normal-case tracking-normal"
              onClick={() => setAsset("ETH")}
              disabled={isBusy}
              role="radio"
              aria-checked={asset === "ETH"}
            >
              ETH
            </Button>
            <Button
              variant={asset === "USDC" ? "default" : "outline"}
              className="w-full font-sans normal-case tracking-normal"
              onClick={() => setAsset("USDC")}
              disabled={isBusy}
              role="radio"
              aria-checked={asset === "USDC"}
            >
              USDC
            </Button>
          </div>
        </div>

        <div className="md:col-span-1">
          <Label className="text-xs text-slate-500 mb-1" htmlFor="donate-purpose">
            Purpose
          </Label>
          <select
            id="donate-purpose"
            name="purpose"
            className="w-full h-10 rounded-md bg-black/20 border border-white/10 text-slate-200 px-3 text-sm rounded-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-sky-400/60"
            value={purposeId}
            onChange={(e) => setPurposeId(Number(e.target.value))}
            disabled={isBusy}
          >
            {purposes.map((p) => (
              <option key={p.id} value={p.id}>
                #{p.id} {p.label}
              </option>
            ))}
          </select>
        </div>

        <div className="md:col-span-1">
          <Label className="text-xs text-slate-500 mb-1" htmlFor="donate-amount">
            Amount
          </Label>
          <input
            id="donate-amount"
            name="amount"
            inputMode="decimal"
            autoComplete="off"
            spellCheck={false}
            className="w-full h-10 rounded-md bg-black/20 border border-white/10 text-slate-200 px-3 text-sm font-mono rounded-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-sky-400/60"
            placeholder={asset === "ETH" ? "0.01…" : "10…"}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            disabled={isBusy}
          />
        </div>

        <div className="md:col-span-1">
          <Label className="text-xs text-slate-500 mb-1" htmlFor="donate-memo">
            Memo (optional)
          </Label>
          <input
            id="donate-memo"
            name="memo"
            autoComplete="off"
            className="w-full h-10 rounded-md bg-black/20 border border-white/10 text-slate-200 px-3 text-sm rounded-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-sky-400/60"
            placeholder="e.g. audit fund…"
            value={memo}
            onChange={(e) => setMemo(e.target.value)}
            disabled={isBusy}
          />
        </div>
      </div>

      {disabledReason ? <div className="text-xs text-amber-200">{disabledReason}</div> : null}

      <div className="flex items-center gap-3">
        <Button className="bg-[#f1f5f9] text-[#0f172a] hover:bg-white font-sans normal-case tracking-normal" onClick={onDonate} disabled={isBusy}>
          {isBusy ? "Sending…" : "Donate"}
        </Button>
        {status ? <div className="text-xs text-slate-400">{status}</div> : null}
      </div>

      {txUrl ? (
        <div className="text-xs text-slate-500">
          Tx:{" "}
          <a
            className="text-sky-300 hover:text-sky-200 underline font-mono break-all rounded-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-sky-400/60"
            href={txUrl}
            target="_blank"
            rel="noreferrer"
          >
            {txHash}
          </a>
        </div>
      ) : null}
    </div>
  );
}

