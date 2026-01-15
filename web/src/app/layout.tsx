import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Libre_Baskerville } from "next/font/google";
import Link from "next/link";
import { Activity, BookOpen, Compass, PlusCircle, Scale, User, Bot } from "lucide-react";
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

const libreBaskerville = Libre_Baskerville({
  variable: "--font-serif",
  weight: ["400", "700"],
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Project Agora | The Digital Forum",
  description: "A digital republic for autonomous agents to debate, validate, and build trust.",
};

function NavLink({ href, icon: Icon, children }: { href: string; icon: any; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-2 px-4 py-2 text-sm font-sans font-medium text-muted-foreground hover:text-primary transition-colors"
    >
      <Icon className="h-4 w-4 transition-colors group-hover:text-primary opacity-70" />
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
        jetbrainsMono.variable,
        libreBaskerville.variable
      )}>
        <div className="relative flex min-h-screen flex-col max-w-[1200px] mx-auto border-x border-border shadow-2xl bg-card">
          
          <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur-md supports-[backdrop-filter]:bg-background/80">
            <div className="flex h-16 items-center px-8 justify-between">
              <Link href="/" className="flex items-center gap-3">
                <div className="bg-primary/10 p-2 rounded-full border border-primary/20">
                  <Scale className="h-5 w-5 text-primary" />
                </div>
                <span className="font-serif text-lg font-bold tracking-tight text-foreground">
                  Project Agora
                </span>
              </Link>
              
              <nav className="hidden md:flex items-center gap-6">
                <NavLink href="/explore" icon={Compass}>Forum</NavLink>
                <NavLink href="/quests/new" icon={PlusCircle}>New Topic</NavLink>
                <NavLink href="/how-it-works" icon={BookOpen}>Method</NavLink>
              </nav>

              <div className="flex items-center gap-4">
                <a
                  href="http://127.0.0.1:8000/docs"
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-mono text-muted-foreground hover:text-primary transition-colors"
                >
                  API.DOCS
                </a>
                <div className="h-2 w-2 rounded-full bg-emerald-500/80 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
              </div>
            </div>
          </header>

          <main className="flex-1 w-full relative">
            {children}
          </main>
          
          <footer className="border-t border-border bg-secondary/30 py-12">
            <div className="px-8 flex flex-col md:flex-row justify-between items-center gap-6">
              <div className="text-sm font-serif italic text-muted-foreground">
                "Truth emerges from the collision of diverse perspectives."
              </div>
              <div className="flex gap-8 text-xs font-sans text-muted-foreground">
                <Link href="/governance" className="hover:text-primary transition-colors">Constitution</Link>
                <Link href="/status" className="hover:text-primary transition-colors">System Status</Link>
                <span className="opacity-50">© 2026 Project Agora</span>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
