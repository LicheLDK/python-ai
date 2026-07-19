import { OcrHistoryAdminPanel } from "@/components/admin/OcrHistoryAdminPanel";

export default function AdminOcrPage() {
  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Admin · OCR history</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        전역 작업 목록 · 결과 drill-down
      </p>
      <OcrHistoryAdminPanel />
    </div>
  );
}
