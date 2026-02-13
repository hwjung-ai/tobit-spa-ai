"use client";

import { PageHeader } from "@/components/shared";
import ChatExperience from "../../../components/chat/ChatExperience";

export default function ApiManagerChatPage() {
  return (
    <div className="flex flex-col h-screen w-screen">
      <PageHeader
        title="API Manager Chat"
        description="API Manager AI 어시스턴트와 대화하며 API를 구성하고 관리합니다."
      />
      <main className="flex-1 overflow-hidden">
        <ChatExperience builderSlug="api-manager" />
      </main>
    </div>
  );
}
