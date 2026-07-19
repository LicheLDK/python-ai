import { PipelinesConsole } from "@/components/pipelines/PipelinesConsole";
import { PageHeader } from "@/components/ui/Card";

export default function PipelinesPage() {
  return (
    <div>
      <PageHeader
        title="Pipelines"
        description="Document → preprocess → OCR → AI → persist"
      />
      <PipelinesConsole />
    </div>
  );
}
