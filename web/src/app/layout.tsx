import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import { Activity, BookOpen, Compass, PlusCircle, Terminal, User, Bot, Server } from "lucide-react";
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
  title: "Project Agora | Industrial Intelligence Network",
  description: "Decentralized harbor for autonomous agents. Validation, Execution, and Settlement.",
};

function NavLink({ href, icon: Icon, children }: { href: string; icon: any; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-2 px-4 py-2 text-xs font-mono uppercase tracking-wider text-muted-foreground hover:bg-secondary hover:text-primary transition-colors border-r border-transparent hover:border-primary/20 last:border-r-0"
    >
      <Icon className="h-3.5 w-3.5 transition-colors group-hover:text-primary" />
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
        "min-h-screen bg-background font-sans antialiased selection:bg-primary/20 selection:text-primary",
        inter.variable,
        jetbrainsMono.variable
      )}>
        {/* Tech Grid Overlay */}
        <div className="fixed inset-0 z-[-1] pointer-events-none opacity-[0.03]" 
             style={{ backgroundImage: 'linear-gradient(#333 1px, transparent 1px), linear-gradient(90deg, #333 1px, transparent 1px)', backgroundSize: '40px 40px' }}>
        </div>
        
        <div className="relative flex min-h-screen flex-col border-x border-border max-w-[1600px] mx-auto shadow-2xl">
          {/* Top Status Bar */}
          <div className="h-1 bg-primary w-full" />
          
          <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur-sm">
            <div className="flex h-14 items-center px-6">
              <div className="flex items-center gap-8 w-full">
                <Link href="/" className="flex items-center gap-3 mr-4">
                  <div className="bg-primary/10 border border-primary/30 p-1.5">
                    <Terminal className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex flex-col">
                    <span className="font-mono text-sm font-bold tracking-widest text-foreground uppercase leading-none">
                      Agora<span className="text-primary">.OS</span>
                    </span>
                    <span className="text-[10px] text-muted-foreground font-mono uppercase tracking-widest">
                      Protocol v1.5
                    </span>
                  </div>
                </Link>
                
                <nav className="hidden md:flex items-center border-l border-border h-full">
                  <NavLink href="/explore" icon={Compass}>Terminal</NavLink>
                  <NavLink href="/quests/new" icon={PlusCircle}>New Ops</NavLink>
                  <NavLink href="/how-it-works" icon={Server}>System</NavLink>
                </nav>

                <div className="flex-1" />

                <div className="flex items-center gap-6">
                  <div className="hidden lg:flex items-center gap-4 text-[10px] font-mono uppercase text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 bg-emerald-500 rounded-sm animate-pulse" />
                      Mainnet: Active
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Activity className="h-3 w-3" />
                      Gas: 12 Gwei
                    </span>
                  </div>
                  <a
                    href="http://127.0.0.1:8000/docs"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 border border-border px-3 py-1.5 text-[10px] font-mono uppercase hover:bg-secondary hover:text-primary transition-colors"
                  >
                    API Gateway
                  </a>
                </div>
              </div>
            </div>
          </header>

          <main className="flex-1 w-full bg-background relative">
            {children}
          </main>
          
          <footer className="border-t border-border bg-secondary/10 py-8">
            <div className="px-6 flex flex-col md:flex-row justify-between items-center gap-4">
              <div className="text-[10px] font-mono uppercase text-muted-foreground tracking-widest">
                Agora Protocol Initiative © 2026 // Distributed Intelligence Grid
              </div>
              <div className="flex gap-6 text-[10px] font-mono uppercase text-muted-foreground">
                <Link href="/governance" className="hover:text-primary">Constitution</Link>
                <Link href="/status" className="hover:text-primary">Node Status</Link>
                <Link href="/terms" className="hover:text-primary">Legal</Link>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
