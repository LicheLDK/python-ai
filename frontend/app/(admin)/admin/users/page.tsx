import { UsersAdminPanel } from "@/components/admin/UsersAdminPanel";
import { PageHeader } from "@/components/ui/Card";

export default function AdminUsersPage() {
  return (
    <div>
      <PageHeader
        title="Admin · Users"
        description="검색 · 역할/상태 변경 · 감사 로그"
      />
      <UsersAdminPanel />
    </div>
  );
}
