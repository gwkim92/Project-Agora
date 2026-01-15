import * as React from "react";
import { cn } from "@/lib/utils";

const Badge = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & { variant?: "default" | "secondary" | "destructive" | "outline" | "success" }>(
  ({ className, variant = "default", ...props }, ref) => {
    const variants: Record<string, string> = {
      default: "border-indigo-500/30 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 shadow-[0_0_10px_rgba(99,102,241,0.1)]",
      secondary: "border-slate-700 bg-slate-800/50 text-slate-400 hover:bg-slate-800",
      destructive: "border-red-900/50 bg-red-900/20 text-red-400 hover:bg-red-900/30",
      outline: "text-slate-400 border-slate-700",
      success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.1)]",
    };
    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
          variants[variant] || variants.default,
          className
        )}
        {...props}
      />
    );
  }
);
Badge.displayName = "Badge";

export { Badge };
