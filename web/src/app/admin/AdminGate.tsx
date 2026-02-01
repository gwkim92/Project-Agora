"use client";

import { useEffect, useState } from "react";

import { bff } from "@/lib/bffClient";
import { connectWallet, personalSign, saveWalletAuth } from "@/lib/walletAuth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function AdminGate({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [ok, setOk] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  async function check() {
    setError(null);
    try {
      const r = await fetch("/api/admin/access/status", { cache: "no-store" }).then((x) => x.json());
      setOk(Boolean(r?.ok));
    } catch {
      setOk(false);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void check();
  }, []);

  async function signToEnter() {
    setError(null);
    setIsBusy(true);
    try {
      const me = await bff.authMe();
      if (!me.authenticated || !me.address) throw new Error("Not signed in");

      // Ensure wallet is connected and matches the signed-in session address.
      const addr = await connectWallet();
      saveWalletAuth({ address: addr, connector: "injected" });
      if (addr.toLowerCase() !== me.address.toLowerCase()) {
        throw new Error("Connected wallet does not match signed-in session address. Log out and sign in with this wallet.");
      }

      const ch = await fetch("/api/admin/access/challenge", { method: "POST" }).then(async (r) => {
        const t = await r.text().catch(() => "");
        if (!r.ok) throw new Error(t || "Failed to request admin challenge");
        return JSON.parse(t) as { message_to_sign: string };
      });
      const sig = await personalSign(addr, ch.message_to_sign);
      await fetch("/api/admin/access/verify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ signature: sig }) }).then(
        async (r) => {
          const t = await r.text().catch(() => "");
          if (!r.ok) throw new Error(t || "Admin access verify failed");
        }
      );
      await check();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Admin access failed");
      setOk(false);
    } finally {
      setIsBusy(false);
    }
  }

  if (loading) return <div className="text-sm text-slate-500">Loading…</div>;
  if (ok) return <>{children}</>;

  return (
    <Card className="border-white/10 bg-white/5">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-slate-200 font-sans">Admin access required</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-slate-300">
        <div className="text-xs text-slate-500">
          To enter the admin dashboard, you must sign an admin-access message with your operator wallet.
        </div>
        {error ? <div className="text-xs text-red-200 break-words">{error}</div> : null}
        <Button onClick={signToEnter} disabled={isBusy}>
          {isBusy ? "Signing…" : "Sign to enter Admin"}
        </Button>
      </CardContent>
    </Card>
  );
}

