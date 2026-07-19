"use client";

import type { InputHTMLAttributes, CSSProperties } from "react";

const wrap: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "0.35rem",
  width: "100%",
};

const labelStyle: CSSProperties = {
  fontSize: "0.85rem",
  fontWeight: 600,
  color: "#374151",
};

const inputStyle: CSSProperties = {
  padding: "0.55rem 0.7rem",
  borderRadius: 6,
  border: "1px solid #d1d5db",
  fontSize: "0.95rem",
  width: "100%",
  boxSizing: "border-box",
};

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, id, style, ...rest }: InputProps) {
  const inputId = id || rest.name;
  return (
    <label style={wrap} htmlFor={inputId}>
      {label ? <span style={labelStyle}>{label}</span> : null}
      <input id={inputId} style={{ ...inputStyle, ...style }} {...rest} />
      {error ? (
        <span style={{ color: "#b91c1c", fontSize: "0.8rem" }}>{error}</span>
      ) : null}
    </label>
  );
}
