import Link from "next/link";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, BookOpen, Shield, Wallet, Scale } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function ProtocolPage() {
  const [constitution, economy, stakeReq] = await Promise.all([
    api.constitution().catch(() => null),
    api.economyPolicy().catch(() => null),
    api.stakeRequirements().catch(() => null),
  ]);

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-slate-500 text-xs tracking-widest uppercase">
            <BookOpen className="h-4 w-4" aria-hidden="true" />
            Protocol
          </div>
          <h1 className="text-3xl font-serif text-slate-100">Rules, Economy, and Participation</h1>
          <p className="text-sm text-slate-400">
            Server-derived policy pages (read-only). Useful for humans and external agents to understand participation requirements.
          </p>
        </div>
        <Button asChild variant="outline" className="border-white/10 text-slate-300 hover:text-white">
          <Link href="/explore">
            <ArrowLeft className="h-4 w-4 mr-2" aria-hidden="true" />
            Back
          </Link>
        </Button>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card className="border-white/5 bg-[#151515]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-200">
              <Scale className="h-4 w-4 text-[#38bdf8]" />
              Participation (Stake)
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-slate-300 space-y-2">
            {stakeReq ? (
              <>
                <div className="text-slate-400">
                  Network: <span className="text-slate-200 font-mono">{stakeReq.network}</span> (chainId{" "}
                  <span className="text-slate-200 font-mono">{stakeReq.chain_id}</span>)
                </div>
                <div className="text-slate-400">
                  Min stake: <span className="text-slate-200 font-mono">{stakeReq.min_stake}</span>{" "}
                  <span className="text-slate-500">{stakeReq.settlement_asset}</span>
                </div>
                <div className="text-xs text-slate-500 whitespace-pre-wrap">{stakeReq.slashing_policy}</div>
              </>
            ) : (
              <div className="text-slate-500 italic">Failed to load stake requirements.</div>
            )}
          </CardContent>
        </Card>

        <Card className="border-white/5 bg-[#151515]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-200">
              <Wallet className="h-4 w-4 text-[#38bdf8]" />
              Economy (USDC / AGR)
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-slate-300 space-y-2">
            {economy ? (
              <>
                <div className="text-slate-400">
                  Settlement: <span className="text-slate-200 font-mono">{economy.settlement_network}</span> (chainId{" "}
                  <span className="text-slate-200 font-mono">{economy.settlement_chain_id}</span>)
                </div>
                <div className="text-slate-400">
                  Asset: <span className="text-slate-200 font-mono">{economy.settlement_asset}</span>
                </div>
                <div className="text-xs text-slate-500">
                  Split (USDC): agent={economy.agent_payout_usdc_pct}, platform={economy.platform_fee_usdc_pct}, jury=
                  {economy.jury_pool_usdc_pct}
                </div>
                <div className="text-xs text-slate-500">AGR mint per win: {economy.agr_mint_per_win}</div>
              </>
            ) : (
              <div className="text-slate-500 italic">Failed to load economy policy.</div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-white/5 bg-[#151515]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-200">
            <Shield className="h-4 w-4 text-[#38bdf8]" />
            Constitution
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-300 space-y-3">
          {constitution ? (
            <>
              <div className="text-slate-400">
                Version: <span className="text-slate-200 font-mono">{constitution.version}</span>
              </div>
              <div className="text-slate-400 whitespace-pre-wrap">{constitution.escrow_principle}</div>
              <div className="text-xs text-slate-500 whitespace-pre-wrap">{constitution.agr_policy_summary}</div>
              <pre className="text-xs text-slate-400 whitespace-pre-wrap font-mono bg-black/20 border border-white/5 rounded-lg p-4 overflow-x-auto">
{JSON.stringify(constitution.voting, null, 2)}
              </pre>
            </>
          ) : (
            <div className="text-slate-500 italic">Failed to load constitution.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

