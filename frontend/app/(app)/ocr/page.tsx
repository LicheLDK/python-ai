import { OcrConsole } from "@/components/ocr/OcrConsole";
import { PageHeader } from "@/components/ui/Card";

export default function OcrPage() {
  return (
    <div>
      <PageHeader
        title="OCR"
        description="문서 선택 → 작업 생성 → 상태 폴링 → 결과"
      />
      <OcrConsole />
    </div>
  );
}
