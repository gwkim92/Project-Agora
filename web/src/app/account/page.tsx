import { AccountSettings } from "./ui";

export default function AccountPage() {
  return (
    <div className="w-full max-w-[900px] mx-auto px-6">
      <div className="mb-8">
        <h1 className="text-2xl font-serif font-bold text-slate-100">Account</h1>
        <p className="text-sm text-slate-400 mt-1">Wallet-based profile: nickname and avatar.</p>
      </div>
      <AccountSettings />
    </div>
  );
}

