"use client";

import type { CSSProperties, ReactNode } from "react";
import { Button } from "@/components/ui/Button";

const backdrop: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(17, 24, 39, 0.45)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 50,
  padding: "1rem",
};

const panel: CSSProperties = {
  background: "#fff",
  borderRadius: 10,
  maxWidth: 520,
  width: "100%",
  padding: "1.25rem",
  boxShadow: "0 10px 30px rgba(0,0,0,0.15)",
};

interface ModalProps {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  footer?: ReactNode;
}

export function Modal({ open, title, children, onClose, footer }: ModalProps) {
  if (!open) return null;
  return (
    <div
      style={backdrop}
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div style={panel} onClick={(e) => e.stopPropagation()}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "0.75rem",
          }}
        >
          <h2 style={{ margin: 0, fontSize: "1.1rem" }}>{title}</h2>
          <Button variant="ghost" onClick={onClose} aria-label="Close">
            ✕
          </Button>
        </div>
        <div>{children}</div>
        {footer ? (
          <div
            style={{
              marginTop: "1rem",
              display: "flex",
              justifyContent: "flex-end",
              gap: "0.5rem",
            }}
          >
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  );
}
