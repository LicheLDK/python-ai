import { OcrConsole } from "@/components/ocr/OcrConsole";

export default function OcrPage() {
  return (
    <div>
      <h1 style={{ marginTop: 0 }}>OCR</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        문서 선택 → 작업 생성 → 상태 폴링 → 결과
      </p>
      <OcrConsole />
    </div>
  );
}
