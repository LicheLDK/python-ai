import { AdminDashboardView } from "@/components/admin/AdminDashboardView";
import { PageHeader } from "@/components/ui/Card";

export default function AdminHomePage() {
  return (
    <div>
      <PageHeader
        title="Admin dashboard"
        description="24h KPI · Top users · Provider breakdown"
      />
      <AdminDashboardView />
    </div>
  );
}
