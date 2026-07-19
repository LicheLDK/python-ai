import { UsageAdminPanel } from "@/components/admin/UsageAdminPanel";

export default function AdminUsagePage() {
  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Admin · AI usage</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        provider / user 필터 · token · cost
      </p>
      <UsageAdminPanel />
    </div>
  );
}
