import { AdminDashboardView } from "@/components/admin/AdminDashboardView";

export default function AdminHomePage() {
  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Admin dashboard</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        전역 KPI (24h) · top users · provider breakdown
      </p>
      <AdminDashboardView />
    </div>
  );
}
