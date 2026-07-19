"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

const variants = {
  primary:
    "bg-brand text-white shadow-sm hover:bg-brand-hover focus-visible:ring-brand/40",
  secondary:
    "bg-white text-foreground border border-border hover:bg-slate-50 focus-visible:ring-brand/20",
  danger:
    "bg-danger text-white hover:bg-red-700 focus-visible:ring-danger/30",
  ghost:
    "bg-transparent text-muted hover:bg-slate-100 hover:text-foreground focus-visible:ring-brand/20",
} as const;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  children: ReactNode;
}

export function Button({
  variant = "primary",
  children,
  className,
  disabled,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl px-3.5 py-2 text-sm font-semibold transition",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
        "disabled:cursor-not-allowed disabled:opacity-55",
        variants[variant],
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
