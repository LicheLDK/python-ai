import { PipelinesConsole } from "@/components/pipelines/PipelinesConsole";

export default function PipelinesPage() {
  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Pipelines</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        Document → preprocess → OCR → AI → persist
      </p>
      <PipelinesConsole />
    </div>
  );
}
