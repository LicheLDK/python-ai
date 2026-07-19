"use client";

import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, id, className, ...rest }: InputProps) {
  const inputId = id || rest.name;
  return (
    <label className="flex w-full flex-col gap-1.5" htmlFor={inputId}>
      {label ? (
        <span className="text-sm font-semibold text-slate-700">{label}</span>
      ) : null}
      <input
        id={inputId}
        className={cn(
          "w-full rounded-xl border border-border bg-white px-3 py-2.5 text-sm text-foreground shadow-sm",
          "placeholder:text-slate-400",
          "focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20",
          error && "border-danger focus:border-danger focus:ring-danger/20",
          className,
        )}
        {...rest}
      />
      {error ? <span className="text-xs text-danger">{error}</span> : null}
    </label>
  );
}
