import { OcrHistoryAdminPanel } from "@/components/admin/OcrHistoryAdminPanel";
import { PageHeader } from "@/components/ui/Card";

export default function AdminOcrPage() {
  return (
    <div>
      <PageHeader
        title="Admin · OCR history"
        description="전역 OCR 작업 · 결과 상세"
      />
      <OcrHistoryAdminPanel />
    </div>
  );
}
