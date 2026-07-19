import {
  ChatPanel,
  PromptBrowser,
  VisionPanel,
} from "@/components/ai/AiPanels";
import { Card, PageHeader } from "@/components/ui/Card";

export default function AiPage() {
  return (
    <div>
      <PageHeader title="AI" description="Chat · Vision · Prompt browser" />
      <div className="grid gap-4">
        <Card className="p-5">
          <ChatPanel />
        </Card>
        <Card className="p-5">
          <VisionPanel />
        </Card>
        <Card className="p-5">
          <PromptBrowser />
        </Card>
      </div>
    </div>
  );
}
