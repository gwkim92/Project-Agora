import * as React from "react";
import { cn } from "@/lib/utils";

const buttonVariants = (variant: string = "default", size: string = "default", className?: string) => {
  const base = "inline-flex items-center justify-center rounded-lg text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]";
  
  const variants: Record<string, string> = {
    default: "bg-slate-50 text-slate-900 hover:bg-slate-200 shadow-[0_0_15px_rgba(255,255,255,0.1)] border border-transparent",
    destructive: "bg-red-900/20 text-red-200 border border-red-900/50 hover:bg-red-900/40 hover:border-red-800",
    outline: "border border-white/10 bg-transparent hover:bg-white/5 text-slate-300 hover:text-white hover:border-white/20",
    secondary: "bg-slate-800/50 text-slate-200 hover:bg-slate-800 border border-white/5 hover:border-white/10",
    ghost: "hover:bg-white/5 hover:text-white text-slate-400",
    link: "text-indigo-400 underline-offset-4 hover:underline",
  };

  const sizes: Record<string, string> = {
    default: "h-10 px-5 py-2",
    sm: "h-8 rounded-md px-3 text-xs",
    lg: "h-12 rounded-xl px-8 text-base",
    icon: "h-9 w-9",
  };

  return cn(base, variants[variant] || variants.default, sizes[size] || sizes.default, className);
};

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
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
