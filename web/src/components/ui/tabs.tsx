import * as React from "react";
import { cn } from "@/lib/utils";

const Tabs = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "w-full",
      className
    )}
    {...props}
  />
));
Tabs.displayName = "Tabs";

const TabsList = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "inline-flex h-12 items-center justify-center rounded-full bg-white/5 p-1 text-slate-400 border border-white/5",
      className
    )}
    {...props}
  />
));
TabsList.displayName = "TabsList";

const TabsTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { value: string; active?: boolean; onClick?: () => void }
>(({ className, active, ...props }, ref) => (
  <button
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center whitespace-nowrap rounded-full px-6 py-2 text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 font-serif tracking-wide",
      active ? "bg-[#f1f5f9] text-[#0f172a] shadow-sm" : "hover:text-white hover:bg-white/5",
      className
    )}
    {...props}
  />
));
TabsTrigger.displayName = "TabsTrigger";

const TabsContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { value: string; activeValue?: string }
>(({ className, value, activeValue, ...props }, ref) => {
  if (value !== activeValue) return null;
  return (
    <div
      ref={ref}
      className={cn(
        "mt-6 ring-offset-background focus-visible:outline-none animate-in fade-in-0 zoom-in-95 duration-300",
        className
      )}
      {...props}
    />
  );
});
TabsContent.displayName = "TabsContent";

export { Tabs, TabsList, TabsTrigger, TabsContent };
