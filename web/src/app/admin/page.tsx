import { notFound } from "next/navigation";

import { getAccessTokenFromCookie } from "@/app/api/_lib/authCookies";
import { serverGetJson } from "@/app/api/_lib/serverApi";
import { AdminGate } from "./AdminGate";
import { AdminDashboard } from "./ui";

export default async function AdminPage() {
  // Hide admin entirely for visitors and non-operators (404).
  const token = await getAccessTokenFromCookie();
  if (!token) return notFound();
  try {
    await serverGetJson("/api/v1/admin/metrics", { token });
  } catch {
    return notFound();
  }
  return (
    <div className="w-full max-w-[1100px] mx-auto px-6">
      <div className="mb-8">
        <h1 className="text-2xl font-serif font-bold text-slate-100">Admin</h1>
        <p className="text-sm text-slate-400 mt-1">Operator-only monitoring (local/staging).</p>
      </div>
      <AdminGate>
        <AdminDashboard />
      </AdminGate>
    </div>
  );
}

