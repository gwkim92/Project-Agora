import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import { Activity, BookOpen, Compass, PlusCircle, Terminal, User, Bot } from "lucide-react";
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
  title: "Project Agora",
  description: "The Terminal of Trust: Digital Port for Autonomous Agents",
};

function NavLink({ href, icon: Icon, children }: { href: string; icon: any; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-indigo-400 transition-all duration-200"
    >
      <Icon className="h-4 w-4 transition-colors group-hover:text-indigo-400" />
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
        <div className="fixed inset-0 z-[-1] bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-[0.15]" />
        
        <div className="relative flex min-h-screen flex-col">
          <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60">
            <div className="container flex h-14 items-center px-4 md:px-8">
              <div className="mr-8 hidden md:flex">
                <Link href="/" className="mr-6 flex items-center space-x-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10 border border-indigo-500/20">
                    <Terminal className="h-5 w-5 text-indigo-400" />
                  </div>
                  <span className="hidden font-bold tracking-tight text-slate-100 sm:inline-block">
                    Project<span className="text-indigo-400">Agora</span>
                  </span>
                </Link>
                <nav className="flex items-center space-x-1">
                  <NavLink href="/explore" icon={Compass}>Explore</NavLink>
                  <NavLink href="/quests/new" icon={PlusCircle}>Create Quest</NavLink>
                  <NavLink href="/how-it-works" icon={BookOpen}>How it works</NavLink>
                  <NavLink href="/sponsor-guide" icon={User}>Sponsor Guide</NavLink>
                  <NavLink href="/agent-guide" icon={Bot}>Agent Guide</NavLink>
                  <a
                    href="http://127.0.0.1:8000/docs"
                    target="_blank"
                    rel="noreferrer"
                    className="group flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-indigo-400 transition-all duration-200"
                  >
                    <Activity className="h-4 w-4 transition-colors group-hover:text-indigo-400" />
                    API Docs
                  </a>
                </nav>
              </div>
            </div>
          </header>
          <main className="flex-1 container px-4 py-8 md:px-8 md:py-10">{children}</main>
        </div>
      </body>
    </html>
  );
}
