import {
  ChatPanel,
  PromptBrowser,
  VisionPanel,
} from "@/components/ai/AiPanels";

export default function AiPage() {
  return (
    <div style={{ display: "grid", gap: "1.5rem" }}>
      <div>
        <h1 style={{ marginTop: 0 }}>AI</h1>
        <p style={{ color: "#4b5563", marginTop: 0 }}>
          Chat · Vision · Prompt browser
        </p>
      </div>
      <section
        style={{
          background: "#fff",
          borderRadius: 8,
          border: "1px solid #e5e7eb",
          padding: "1rem",
        }}
      >
        <ChatPanel />
      </section>
      <section
        style={{
          background: "#fff",
          borderRadius: 8,
          border: "1px solid #e5e7eb",
          padding: "1rem",
        }}
      >
        <VisionPanel />
      </section>
      <section
        style={{
          background: "#fff",
          borderRadius: 8,
          border: "1px solid #e5e7eb",
          padding: "1rem",
        }}
      >
        <PromptBrowser />
      </section>
    </div>
  );
}
