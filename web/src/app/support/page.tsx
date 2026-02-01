import Link from "next/link";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { HeartHandshake, ArrowLeft } from "lucide-react";
import { DonateWidget } from "@/components/DonateWidget";

export const dynamic = "force-dynamic";

const PURPOSES: Array<{ id: number; label: string; examples: string }> = [
  { id: 1, label: "Ops", examples: "Security reviews, monitoring, incident response, runbooks" },
  { id: 2, label: "Rewards", examples: "Bounty payouts, jury incentives, community programs" },
  { id: 3, label: "Audits", examples: "Contract audits, bug bounty pool" },
  { id: 4, label: "Research", examples: "Protocol research, experiments, tooling" },
];

function isZeroAddress(addr: string | null | undefined): boolean {
  if (!addr) return true;
  return addr.toLowerCase() === "0x0000000000000000000000000000000000000000";
}

function explorerBaseForChainId(chainId: number): string | null {
  // Base mainnet / Base Sepolia
  if (chainId === 8453) return "https://basescan.org";
  if (chainId === 84532) return "https://sepolia.basescan.org";
  return null;
}

export default async function SupportPage() {
  const constitution = await api.constitution().catch(() => null);
  const treasury = constitution?.treasury ?? null;
  const chainId = treasury?.chain_id ?? null;
  const explorer = chainId ? explorerBaseForChainId(chainId) : null;
  const contractAddress = treasury?.contract_address ?? null;
  const contractExplorerUrl = explorer && contractAddress && !isZeroAddress(contractAddress) ? `${explorer}/address/${contractAddress}` : null;

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-slate-500 text-xs tracking-widest uppercase">
            <HeartHandshake className="h-4 w-4" aria-hidden="true" />
            Support
          </div>
          <h1 className="text-3xl font-serif text-slate-100">Donate / Support the Treasury</h1>
          <p className="text-sm text-slate-400">
            Donations are onchain (Base) and are designed to be fully transparent (inflows/outflows + purpose buckets).
          </p>
        </div>
        <Button asChild variant="outline" className="border-white/10 text-slate-300 hover:text-white">
          <Link href="/explore">
            <ArrowLeft className="h-4 w-4 mr-2" aria-hidden="true" />
            Back
          </Link>
        </Button>
      </div>

      <Card className="border-white/5 bg-[#151515]">
        <CardHeader>
          <CardTitle className="text-slate-200">How it works</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-300 space-y-4">
          <div className="text-slate-400">
            We accept <span className="text-slate-200 font-mono">ETH</span> and <span className="text-slate-200 font-mono">USDC</span>.
            All inflows and outflows are recorded via onchain events and purpose-bucket accounting.
          </div>
          {treasury ? (
            <div className="text-xs text-slate-500 space-y-1">
              <div>
                Network: <span className="text-slate-200 font-mono">{treasury.network}</span>
                {typeof chainId === "number" ? (
                  <>
                    {" "}
                    (chainId <span className="text-slate-200 font-mono">{chainId}</span>)
                  </>
                ) : null}
              </div>
              <div>
                Treasury contract:{" "}
                {contractAddress && !isZeroAddress(contractAddress) ? (
                  <span className="text-slate-200 font-mono break-all">{contractAddress}</span>
                ) : (
                  <span className="text-slate-500 italic">Not deployed yet (zero-address)</span>
                )}
              </div>
              <div>
                USDC: <span className="text-slate-200 font-mono break-all">{treasury.usdc_address}</span>
              </div>
              {contractExplorerUrl ? (
                <div>
                  Explorer:{" "}
                  <a
                    className="text-sky-300 hover:text-sky-200 underline rounded-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-sky-400/60"
                    href={contractExplorerUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    View on Basescan
                  </a>
                </div>
              ) : null}
              {treasury.note ? <div className="text-slate-600">{treasury.note}</div> : null}
            </div>
          ) : (
            <div className="text-slate-500 text-xs italic">Failed to load treasury config from server.</div>
          )}
        </CardContent>
      </Card>

      <Card className="border-white/5 bg-[#151515]">
        <CardHeader>
          <CardTitle className="text-slate-200">Donate</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-300 space-y-3">
          <div className="text-slate-400">
            Click-to-donate via your wallet. Choose <span className="font-mono text-slate-200">ETH</span> or{" "}
            <span className="font-mono text-slate-200">USDC</span>, then confirm the transaction in MetaMask / WalletConnect.
          </div>
          <DonateWidget
            treasury={treasury}
            purposes={[
              { id: 1, label: "Ops" },
              { id: 2, label: "Rewards" },
              { id: 3, label: "Audits" },
              { id: 4, label: "Research" },
            ]}
          />
          <div className="text-xs text-slate-500">
            Note: The platform does <span className="text-slate-200">not</span> sponsor gas. Your wallet will pay the network fee.
          </div>
        </CardContent>
      </Card>

      <Card className="border-white/5 bg-[#151515]">
        <CardHeader>
          <CardTitle className="text-slate-200">Purpose buckets</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-300">
          <div className="divide-y divide-white/5">
            {PURPOSES.map((p) => (
              <div key={p.id} className="py-3 flex items-start justify-between gap-6">
                <div>
                  <div className="text-slate-200 font-mono">
                    #{p.id} {p.label}
                  </div>
                  <div className="text-xs text-slate-500">{p.examples}</div>
                </div>
                <div className="text-xs text-slate-600 font-mono">purposeId={p.id}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

