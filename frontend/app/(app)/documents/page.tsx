import { DocumentsPanel } from "@/components/documents/DocumentsPanel";

export default function DocumentsPage() {
  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Documents</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        업로드 · 목록 · 삭제 (jpeg/png/webp/pdf)
      </p>
      <DocumentsPanel />
    </div>
  );
}
