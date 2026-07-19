import { PromptManager } from "@/components/admin/PromptManager";

export default function AdminPromptsPage() {
  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Admin · Prompts</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        생성 · 버전 · activate (기존 `/ai/prompts*` API)
      </p>
      <PromptManager />
    </div>
  );
}
