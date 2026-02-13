"use client";

import { PageHeader } from "@/components/shared";
import ChatExperience from "../../../components/chat/ChatExperience";

export default function CepBuilderChatPage() {
  return (
    <div className="flex flex-col h-screen w-screen">
      <PageHeader
        title="CEP Builder Chat"
        description="CEP Builder AI 어시스턴트와 대화하며 CEP 규칙을 구성하고 관리합니다."
      />
      <main className="flex-1 overflow-hidden">
        <ChatExperience builderSlug="cep-builder" />
      </main>
    </div>
  );
}
