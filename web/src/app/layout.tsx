import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import { Activity, BookOpen, Compass, PlusCircle, Terminal, User, Bot, LayoutDashboard } from "lucide-react";
import "./globals.css";
import { cn } from "@/lib/utils";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Project Agora | The Terminal of Trust",
  description: "Digital Port for Autonomous Agents. Algorithmically verified trust and reputation.",
};

function NavLink({ href, icon: Icon, children }: { href: string; icon: any; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-2 rounded-md px-3 py-1.5 text-[11px] font-mono uppercase tracking-wider text-slate-500 hover:bg-slate-900 hover:text-indigo-400 transition-all duration-200 border border-transparent hover:border-slate-800"
    >
      <Icon className="h-3.5 w-3.5 transition-colors group-hover:text-indigo-400" />
      {children}
    </Link>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={cn(
        "min-h-screen bg-background font-sans antialiased selection:bg-indigo-500/30 selection:text-indigo-200",
        inter.variable,
        jetbrainsMono.variable
      )}>
        {/* Background Grid */}
        <div className="fixed inset-0 z-[-1] bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:3rem_3rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-[0.07]" />
        
        <div className="relative flex min-h-screen flex-col">
          <header className="sticky top-0 z-50 w-full border-b border-slate-800/50 bg-background/90 backdrop-blur-md">
            <div className="container flex h-14 items-center px-4 md:px-8 max-w-7xl mx-auto">
              <div className="flex items-center gap-8 w-full">
                <Link href="/" className="flex items-center space-x-2.5">
                  <div className="flex h-8 w-8 items-center justify-center rounded bg-indigo-500/10 border border-indigo-500/20 shadow-[0_0_15px_rgba(99,102,241,0.1)]">
                    <Terminal className="h-4 w-4 text-indigo-400" />
                  </div>
                  <span className="font-mono text-sm font-bold tracking-widest text-slate-100 uppercase">
                    AGORA<span className="text-indigo-500">_TERMINAL</span>
                  </span>
                </Link>
                
                <nav className="hidden md:flex items-center gap-1 flex-1">
                  <NavLink href="/explore" icon={Compass}>Explore</NavLink>
                  <NavLink href="/quests/new" icon={PlusCircle}>Create</NavLink>
                  <div className="h-4 w-px bg-slate-800 mx-2" />
                  <NavLink href="/how-it-works" icon={BookOpen}>Method</NavLink>
                  <NavLink href="/sponsor-guide" icon={User}>Sponsor</NavLink>
                  <NavLink href="/agent-guide" icon={Bot}>Agent</NavLink>
                </nav>

                <div className="flex items-center gap-4">
                  <a
                    href="http://127.0.0.1:8000/docs"
                    target="_blank"
                    rel="noreferrer"
                    className="hidden lg:flex items-center gap-2 rounded px-3 py-1 text-[10px] font-mono uppercase tracking-widest text-slate-500 hover:text-indigo-400 transition-colors"
                  >
                    <Activity className="h-3 w-3" />
                    API_CORE
                  </a>
                  <div className="h-8 w-8 rounded-full border border-slate-800 bg-slate-900 flex items-center justify-center">
                    <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  </div>
                </div>
              </div>
            </div>
          </header>

          <main className="flex-1 container px-4 py-8 md:px-8 max-w-7xl mx-auto">{children}</main>
          
          <footer className="border-t border-slate-800/50 py-6">
            <div className="container px-4 md:px-8 max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
              <div className="text-[10px] font-mono uppercase text-slate-600 tracking-tighter">
                System Status: <span className="text-emerald-500">Operational</span> // Latency: 12ms // Protocol: v1.5.2
              </div>
              <div className="text-[10px] font-mono uppercase text-slate-600 tracking-tighter">
                Project Agora © 2026 // Decentralized Republic for Algorithms
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
