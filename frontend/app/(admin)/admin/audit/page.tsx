import { AuditAdminPanel } from "@/components/admin/AuditAdminPanel";

export default function AdminAuditPage() {
  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Admin · Audit</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        action 필터 · admin patch 등 감사 로그
      </p>
      <AuditAdminPanel />
    </div>
  );
}
