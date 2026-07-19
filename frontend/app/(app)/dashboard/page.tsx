import { DashboardView } from "@/components/stats/DashboardView";

export default function DashboardPage() {
  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Dashboard</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        오늘 요약 · 일별 차트 · 최근 OCR
      </p>
      <DashboardView />
    </div>
  );
}
