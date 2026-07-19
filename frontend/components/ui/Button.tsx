"use client";

import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from "react";

const base: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: "0.4rem",
  padding: "0.5rem 0.9rem",
  borderRadius: 6,
  border: "1px solid transparent",
  fontSize: "0.9rem",
  fontWeight: 600,
  cursor: "pointer",
  lineHeight: 1.2,
};

const variants: Record<string, CSSProperties> = {
  primary: { background: "#1a56db", color: "#fff" },
  secondary: {
    background: "#fff",
    color: "#1f2937",
    border: "1px solid #d1d5db",
  },
  danger: { background: "#b91c1c", color: "#fff" },
  ghost: { background: "transparent", color: "#1f2937" },
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  children: ReactNode;
}

export function Button({
  variant = "primary",
  children,
  style,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      style={{
        ...base,
        ...variants[variant],
        opacity: disabled ? 0.55 : 1,
        cursor: disabled ? "not-allowed" : "pointer",
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  );
}
