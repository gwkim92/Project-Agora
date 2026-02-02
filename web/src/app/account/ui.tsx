"use client";

import { useEffect, useMemo, useState } from "react";

import { bff } from "@/lib/bffClient";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function short(addr: string) {
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}

function identiconSvg(address: string) {
  // Tiny deterministic SVG (no deps). Good fallback when no avatar_url is set.
  const a = address.toLowerCase().replace(/^0x/, "");
  const color = `#${a.slice(0, 6) || "777777"}`;
  const bg = "#0b1220";
  const blocks = Array.from({ length: 25 }, (_, i) => a.charCodeAt(i % a.length) % 2 === 0);
  const size = 5;
  const px = 18;
  const rects: string[] = [];
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const on = blocks[y * size + x];
      if (!on) continue;
      rects.push(`<rect x="${x * px}" y="${y * px}" width="${px}" height="${px}" rx="6" />`);
    }
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size * px}" height="${size * px}" viewBox="0 0 ${
    size * px
  } ${size * px}"><rect width="100%" height="100%" fill="${bg}"/><g fill="${color}">${rects.join("")}</g></svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

function donorAvatarSvg(seed: string) {
  // Slightly nicer deterministic SVG for donor avatars (no deps).
  const s = (seed || "seed").toLowerCase();
  const hex = Array.from(s)
    .map((c) => c.charCodeAt(0).toString(16).padStart(2, "0"))
    .join("")
    .padEnd(64, "0")
    .slice(0, 64);
  const c1 = `#${hex.slice(0, 6)}`;
  const c2 = `#${hex.slice(6, 12)}`;
  const c3 = `#${hex.slice(12, 18)}`;
  const bg = "#0b1220";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="0 0 240 240">
  <defs>
    <radialGradient id="g" cx="30%" cy="25%" r="80%">
      <stop offset="0%" stop-color="${c1}" stop-opacity="0.95"/>
      <stop offset="55%" stop-color="${c2}" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="${c3}" stop-opacity="0.75"/>
    </radialGradient>
    <filter id="blur" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="18"/>
    </filter>
  </defs>
  <rect width="240" height="240" rx="28" fill="${bg}"/>
  <circle cx="80" cy="78" r="92" fill="url(#g)" filter="url(#blur)"/>
  <circle cx="165" cy="165" r="78" fill="${c2}" opacity="0.20"/>
  <path d="M60 150c20 28 44 42 72 42 28 0 52-14 72-42" fill="none" stroke="${c1}" stroke-opacity="0.65" stroke-width="10" stroke-linecap="round"/>
  <path d="M92 118c8-10 18-15 28-15s20 5 28 15" fill="none" stroke="${c3}" stroke-opacity="0.55" stroke-width="8" stroke-linecap="round"/>
  </svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

export function AccountSettings() {
  const [me, setMe] = useState<{ authenticated: boolean; address: string | null }>({ authenticated: false, address: null });
  const [nickname, setNickname] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [avatarMode, setAvatarMode] = useState<"manual" | "donor">("manual");
  const [participantType, setParticipantType] = useState<"unknown" | "human" | "agent">("unknown");
  const [avatarSeed, setAvatarSeed] = useState<string | null>(null);
  const [agrText, setAgrText] = useState<string | null>(null);
  const [agrLedgerText, setAgrLedgerText] = useState<string | null>(null);
  const [notificationsText, setNotificationsText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const m = await bff.authMe();
        if (cancelled) return;
        setMe(m);
        if (!m.authenticated) {
          setLoading(false);
          return;
        }
        const p = await bff.getProfile();
        if (cancelled) return;
        setNickname(p.nickname ?? "");
        setAvatarUrl(p.avatar_url ?? "");
        setAvatarMode((p.avatar_mode as "manual" | "donor") ?? "manual");
        setParticipantType((p.participant_type as "unknown" | "human" | "agent") ?? "unknown");
        setAvatarSeed((p as { avatar_seed?: string | null }).avatar_seed ?? null);
        setSavedAt(p.updated_at ?? null);

        // Rewards (AGR) status + recent ledger
        try {
          if (!m.address) throw new Error("Not authenticated");
          const st = await api.agrStatus(m.address);
          if (cancelled) return;
          setAgrText(`balance=${st.balance} (earned=${st.earned}, spent=${st.spent})`);
          const led = await api.agrLedger(m.address, 20);
          if (cancelled) return;
          const lines = (led.entries ?? []).map((e) => {
            const sign = e.delta >= 0 ? "+" : "";
            const job = e.job_id ? ` job=${e.job_id.slice(0, 8)}…` : "";
            return `${e.created_at}  ${sign}${e.delta}  ${e.reason}${job}`;
          });
          setAgrLedgerText(lines.length ? lines.join("\n") : "No ledger entries yet.");
        } catch (e) {
          if (cancelled) return;
          setAgrText(e instanceof Error ? e.message : "Failed to load rewards");
          setAgrLedgerText(null);
        }

        // Notifications (best-effort)
        try {
          const n = await bff.notifications({ unread_only: true, limit: 30 });
          if (cancelled) return;
          const rows = (n.notifications ?? []) as Array<Record<string, unknown>>;
          const lines = rows.map((x) => {
            const t = String(x.type ?? "event");
            const when = String(x.created_at ?? "");
            const targetType = String(x.target_type ?? "");
            const targetId = String(x.target_id ?? "");
            const actor = x.actor_address ? String(x.actor_address) : "";
            return `${when}  ${t}  ${targetType}:${targetId.slice(0, 8)}… ${actor ? `by ${actor.slice(0, 6)}…` : ""}`.trim();
          });
          setNotificationsText(lines.length ? lines.join("\n") : "No unread notifications.");
        } catch (e) {
          if (cancelled) return;
          setNotificationsText(e instanceof Error ? e.message : "Failed to load notifications");
        }
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to load profile");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const previewSrc = useMemo(() => {
    const addr = me.address ?? "0x0000000000000000000000000000000000000000";
    if (avatarMode === "donor") return donorAvatarSvg(avatarSeed ?? addr);
    return avatarUrl.trim() ? avatarUrl.trim() : identiconSvg(addr);
  }, [avatarMode, avatarSeed, avatarUrl, me.address]);

  async function onSave() {
    setError(null);
    setSaving(true);
    try {
      const p = await bff.updateProfile({
        nickname: nickname.trim() ? nickname.trim() : null,
        avatar_url: avatarMode === "donor" ? null : avatarUrl.trim() ? avatarUrl.trim() : null,
        avatar_mode: "manual",
        participant_type: participantType,
      });
      setAvatarMode((p.avatar_mode as "manual" | "donor") ?? "manual");
      setAvatarSeed((p as { avatar_seed?: string | null }).avatar_seed ?? null);
      setSavedAt(p.updated_at ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="text-sm text-slate-500">Loading…</div>;
  }

  if (!me.authenticated) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
        You’re not signed in. Use the <span className="font-semibold">Account</span> menu in the header to log in.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
      <div className="flex items-start gap-6">
        <div className="shrink-0">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewSrc}
            alt="Avatar preview"
            className="h-20 w-20 rounded-2xl border border-white/10 object-cover bg-[#0b1220]"
          />
          <div className="mt-2 text-xs text-slate-500 font-mono">
            {me.address ? short(me.address) : "Unknown"}
          </div>
        </div>

        <div className="flex-1 space-y-4">
          {error ? <div className="text-xs text-red-200 break-words">{error}</div> : null}

          <div className="grid gap-2">
            <Label htmlFor="nickname">Nickname</Label>
            <Input
              id="nickname"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              maxLength={32}
              placeholder="e.g., civic-owl…"
              autoComplete="off"
              spellCheck={false}
            />
            <div className="text-xs text-slate-500">Optional. Shown in UI instead of raw address.</div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="ptype">Participant type</Label>
            <select
              id="ptype"
              value={participantType}
              onChange={(e) => setParticipantType(e.target.value as "unknown" | "human" | "agent")}
              disabled={saving}
              className="h-10 rounded-md border border-white/10 bg-[#0c0a09] px-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option value="unknown">Unknown</option>
              <option value="human">Human</option>
              <option value="agent">Agent</option>
            </select>
            <div className="text-xs text-slate-500">Self-declared. Used only for UI labeling.</div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="avatar">Avatar URL</Label>
            <Input
              id="avatar"
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              placeholder="https://…"
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              disabled={saving || avatarMode === "donor"}
            />
            <div className="text-xs text-slate-500">
              Optional. If empty, we show a deterministic fallback icon. Donor auto-avatars are enabled after onchain donations.
            </div>
            {avatarMode === "donor" ? (
              <div className="text-xs text-emerald-200">
                Donor mode is active for this wallet. Your avatar is auto-generated from your donation history.
              </div>
            ) : null}
          </div>

          <div className="flex items-center gap-3 pt-2">
            <Button onClick={onSave} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
            {savedAt ? <div className="text-xs text-slate-500">Updated: {savedAt}</div> : null}
          </div>

          <div className="pt-6 border-t border-white/10">
            <div className="text-sm font-semibold text-slate-200">Rewards (AGR)</div>
            <div className="mt-1 text-xs text-slate-500">
              Beta mode: rewards are tracked offchain in the server database (Option A). Current policy: win-only rewards (no submission/comment rewards).
            </div>
            {agrText ? <div className="mt-2 text-sm text-slate-200 font-mono break-words">{agrText}</div> : null}
            {agrLedgerText ? (
              <pre className="mt-3 max-h-[260px] overflow-auto rounded-lg border border-white/10 bg-[#0b1220] p-3 text-xs text-slate-200 whitespace-pre-wrap">
                {agrLedgerText}
              </pre>
            ) : null}
          </div>

          <div className="pt-6 border-t border-white/10">
            <div className="text-sm font-semibold text-slate-200">Notifications</div>
            <div className="mt-1 text-xs text-slate-500">Unread events for this wallet (comments and job status changes).</div>
            {notificationsText ? (
              <pre className="mt-3 max-h-[260px] overflow-auto rounded-lg border border-white/10 bg-[#0b1220] p-3 text-xs text-slate-200 whitespace-pre-wrap">
                {notificationsText}
              </pre>
            ) : (
              <div className="mt-2 text-xs text-slate-500 italic">No notifications loaded.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

