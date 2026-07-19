import { PromptManager } from "@/components/admin/PromptManager";
import { PageHeader } from "@/components/ui/Card";

export default function AdminPromptsPage() {
  return (
    <div>
      <PageHeader
        title="Admin · Prompts"
        description="버전 생성 · 활성화 · 템플릿 관리"
      />
      <PromptManager />
    </div>
  );
}
