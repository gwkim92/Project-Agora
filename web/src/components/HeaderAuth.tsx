"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  clearWalletAuth,
  connectInjectedWallet,
  connectWalletConnect,
  ensureInjectedChain,
  loadWalletAuth,
  personalSign,
  saveWalletAuth,
} from "@/lib/walletAuth";
import { bff } from "@/lib/bffClient";
import { AGORA_API_BASE, AGORA_CHAIN_ID } from "@/lib/config";

function short(addr: string) {
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}

export function HeaderAuth() {
  const [address, setAddress] = useState<string | null>(null);
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasInjected, setHasInjected] = useState<boolean>(false);
  const [open, setOpen] = useState(false);
  const [nickname, setNickname] = useState<string | null>(null);
  const [isOperator, setIsOperator] = useState(false);
  const [requiredChainId, setRequiredChainId] = useState<number>(AGORA_CHAIN_ID);
  const [currentChainId, setCurrentChainId] = useState<number | null>(null);
  // If we ever want to show session wallet distinct from connected wallet, we can re-introduce this.
  // const [sessionAddress, setSessionAddress] = useState<string | null>(null);

  useEffect(() => {
    const s = loadWalletAuth();
    setAddress(s.address);
    setHasInjected(Boolean((window as unknown as { ethereum?: { request?: unknown } }).ethereum?.request));
    bff
      .authMe()
      .then((me) => {
        const ok = Boolean(me.authenticated);
        setIsSignedIn(ok);
        if (!ok) {
          setNickname(null);
          setIsOperator(false);
          return;
        }
        bff
          .getProfile()
          .then((p) => setNickname(p.nickname ?? null))
          .catch(() => setNickname(null));
        // Operator detection: admin endpoint is operator-only (403 otherwise).
        bff
          .adminMetrics()
          .then(() => setIsOperator(true))
          .catch(() => setIsOperator(false));
      })
      .catch(() => {
        setIsSignedIn(false);
        setNickname(null);
        setIsOperator(false);
      });

    // Public chain requirements (no auth).
    fetch(`${AGORA_API_BASE}/api/v1/stake/requirements`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        const cid = Number(j?.chain_id);
        if (Number.isFinite(cid) && cid > 0) setRequiredChainId(cid);
      })
      .catch(() => {});

    // Current wallet chain id (best-effort).
    const eth = (window as unknown as { ethereum?: { request?: (args: { method: string; params?: unknown[] }) => Promise<unknown> } }).ethereum;
    eth?.request?.({ method: "eth_chainId" })
      .then((hex) => {
        const n = parseInt(String(hex), 16);
        if (Number.isFinite(n)) setCurrentChainId(n);
      })
      .catch(() => {});
  }, []);

  function onInstallMetaMask() {
    window.open("https://metamask.io/download/", "_blank", "noopener,noreferrer");
  }

  async function connectAndSignIn(connector: "injected" | "walletconnect") {
    setError(null);
    setIsBusy(true);
    try {
      if (connector === "injected") {
        // Make MetaMask show our network (switch/add) before sign-in.
        await ensureInjectedChain(requiredChainId);
        setCurrentChainId(requiredChainId);
      }
      const addr =
        connector === "injected" ? await connectInjectedWallet() : await connectWalletConnect();

      setAddress(addr);
      saveWalletAuth({ address: addr, connector });

      // Treat “wallet connect” as “login”: immediately create Agora session via signature.
      const ch = await bff.authChallenge(addr);
      const sig = await personalSign(addr, ch.message_to_sign);
      await bff.authVerify(addr, sig);
      setIsSignedIn(true);
      // Refresh profile/operator state immediately after login (without requiring a full page reload).
      bff
        .getProfile()
        .then((p) => setNickname(p.nickname ?? null))
        .catch(() => setNickname(null));
      bff
        .adminMetrics()
        .then(() => setIsOperator(true))
        .catch(() => setIsOperator(false));
      setOpen(false);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Login failed";
      setError(msg);
      setIsSignedIn(false);
      setIsOperator(false);
    } finally {
      setIsBusy(false);
    }
  }

  async function onSignOut() {
    setError(null);
    setIsBusy(true);
    try {
      await bff.authLogout();
      setIsSignedIn(false);
      // Forget cached wallet address so UI doesn't look "logged in" after logout.
      clearWalletAuth();
      setAddress(null);
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-out failed");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <div className="relative">
      <Button
        variant="outline"
        className="h-9 px-3 border-white/10 text-slate-200 hover:text-white font-sans normal-case tracking-normal"
        onClick={() => setOpen((v) => !v)}
        disabled={isBusy}
        title={isSignedIn ? "Signed in" : "Not signed in"}
      >
        {/* Avoid confusion: show wallet identity only when the Agora session is signed in. */}
        {isSignedIn ? (nickname ? nickname : address ? short(address) : "Account") : "Account"}
        <span
          className={
            "ml-2 px-2 py-[2px] rounded-full text-[10px] font-sans border " +
            (isSignedIn ? "bg-emerald-500/10 text-emerald-200 border-emerald-500/20" : "bg-slate-500/10 text-slate-300 border-white/10")
          }
        >
          {isSignedIn ? "Signed" : "Guest"}
        </span>
      </Button>

      {open ? (
        <div className="absolute right-0 mt-2 w-[320px] rounded-xl border border-white/10 bg-[#151515] shadow-xl p-3 z-50">
          <div className="flex items-center justify-between gap-2">
            <div className="text-xs text-slate-400">
              {address ? (
                <>
                  Connected wallet (local): <span className="font-mono text-slate-200">{short(address)}</span>
                </>
              ) : (
                <span className="italic">No wallet connected</span>
              )}
            </div>
            <button className="text-xs text-slate-500 hover:text-slate-200" onClick={() => setOpen(false)}>
              Close
            </button>
          </div>

          {error ? <div className="mt-2 text-xs text-red-200 break-words">{error}</div> : null}

          <div className="mt-3 text-xs text-slate-500">
            Required network: <span className="text-slate-200 font-mono">chainId {requiredChainId}</span>
            {currentChainId ? (
              <>
                {" "}
                · Wallet: <span className="text-slate-200 font-mono">chainId {currentChainId}</span>
              </>
            ) : null}
            {currentChainId && currentChainId !== requiredChainId ? (
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="text-amber-200">Network mismatch</span>
                <Button
                  variant="outline"
                  className="h-8 px-2 border-white/10 text-slate-200 hover:text-white text-xs"
                  onClick={async () => {
                    try {
                      setError(null);
                      await ensureInjectedChain(requiredChainId);
                      setCurrentChainId(requiredChainId);
                    } catch (e) {
                      setError(e instanceof Error ? e.message : "Failed to switch network");
                    }
                  }}
                >
                  Switch
                </Button>
              </div>
            ) : null}
          </div>

          <div className="mt-3 space-y-2">
            <div className="text-[11px] text-slate-500">Profile</div>
            <div className="flex items-center justify-between">
              <a
                href="/account"
                className="text-xs text-slate-300 hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 rounded-md px-2 py-2"
              >
                Edit profile
              </a>
              {isOperator ? (
                <a
                  href="/admin"
                  className="text-xs text-slate-300 hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 rounded-md px-2 py-2"
                  title="Operator"
                >
                  Admin
                </a>
              ) : null}
            </div>

            <div className="text-[11px] text-slate-500">Login</div>
            <div className="flex gap-2">
              {hasInjected ? (
                <Button
                  className="h-9 px-3 bg-[#f1f5f9] text-[#0f172a] hover:bg-white font-sans normal-case tracking-normal"
                  onClick={() => connectAndSignIn("injected")}
                  disabled={isBusy}
                >
                  MetaMask
                </Button>
              ) : (
                <Button
                  variant="outline"
                  className="h-9 px-3 border-white/10 text-slate-200 hover:text-white font-sans normal-case tracking-normal"
                  onClick={onInstallMetaMask}
                  disabled={isBusy}
                >
                  Install MetaMask
                </Button>
              )}

              <Button
                variant="outline"
                className="h-9 px-3 border-white/10 text-slate-200 hover:text-white font-sans normal-case tracking-normal"
                onClick={() => connectAndSignIn("walletconnect")}
                disabled={isBusy}
                title="WalletConnect: mobile/QR/no extension"
              >
                WalletConnect
              </Button>
            </div>

            <div className="text-[11px] text-slate-500 mt-2">Session</div>
            <div className="flex items-center justify-between">
              <div className="text-xs text-slate-400">
                Status: <span className="text-slate-200">{isSignedIn ? "Signed in" : "Not signed in"}</span>
              </div>
              {isSignedIn ? (
                <Button
                  variant="ghost"
                  className="h-9 px-3 text-slate-400 hover:text-white font-sans normal-case tracking-normal"
                  onClick={onSignOut}
                  disabled={isBusy}
                >
                  Log out
                </Button>
              ) : address ? (
                <Button
                  variant="ghost"
                  className="h-9 px-3 text-slate-500 hover:text-slate-200 font-sans normal-case tracking-normal"
                  onClick={() => {
                    clearWalletAuth();
                    setAddress(null);
                  }}
                  disabled={isBusy}
                  title="Forget cached wallet address (does not disconnect MetaMask)"
                >
                  Forget wallet
                </Button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

