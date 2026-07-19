import { UsageAdminPanel } from "@/components/admin/UsageAdminPanel";
import { PageHeader } from "@/components/ui/Card";

export default function AdminUsagePage() {
  return (
    <div>
      <PageHeader
        title="Admin · AI usage"
        description="토큰 · 프로바이더 · 사용자별 사용량"
      />
      <UsageAdminPanel />
    </div>
  );
}
