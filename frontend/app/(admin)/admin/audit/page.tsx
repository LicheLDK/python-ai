import { AuditAdminPanel } from "@/components/admin/AuditAdminPanel";
import { PageHeader } from "@/components/ui/Card";

export default function AdminAuditPage() {
  return (
    <div>
      <PageHeader
        title="Admin · Audit"
        description="관리자 액션 · 로그인 실패 등"
      />
      <AuditAdminPanel />
    </div>
  );
}
