import * as React from "react";
import { cn } from "@/lib/utils";

const buttonVariants = (variant: string = "default", size: string = "default", className?: string) => {
  const base = "inline-flex items-center justify-center rounded-md text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]";
  
  const variants: Record<string, string> = {
    default: "bg-indigo-600 text-white shadow-[0_0_15px_rgba(99,102,241,0.3)] hover:bg-indigo-500 hover:shadow-[0_0_20px_rgba(99,102,241,0.5)] border border-indigo-500/50",
    destructive: "bg-red-900/50 text-red-200 border border-red-800 hover:bg-red-900 hover:text-red-100",
    outline: "border border-slate-700 bg-transparent hover:bg-slate-800 text-slate-300 hover:text-white",
    secondary: "bg-slate-800 text-slate-200 hover:bg-slate-700 border border-slate-700",
    ghost: "hover:bg-slate-800 hover:text-white text-slate-400",
    link: "text-indigo-400 underline-offset-4 hover:underline",
  };

  const sizes: Record<string, string> = {
    default: "h-9 px-4 py-2",
    sm: "h-8 rounded-md px-3 text-xs",
    lg: "h-10 rounded-md px-8",
    icon: "h-9 w-9",
  };

  return cn(base, variants[variant] || variants.default, sizes[size] || sizes.default, className);
};

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
  /**
   * When true, renders the child element (e.g. next/link or <a>) with button styles.
   * This mimics shadcn/radix "asChild" pattern without adding extra deps.
   */
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", asChild = false, children, ...props }, ref) => {
    const classes = buttonVariants(variant, size, className);

    if (asChild && React.isValidElement(children)) {
      const child = children as React.ReactElement<any>;
      return React.cloneElement(child, {
        ...props,
        className: cn(classes, child.props?.className),
      });
    }

    return (
      <button className={classes} ref={ref} {...props}>
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
