"use client";

import React from "react";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  secondaryAction,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      {icon && (
        <div className="mb-4 text-muted-foreground opacity-50">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-medium mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-sm mb-6">
        {description}
      </p>
      <div className="flex gap-2">
        {secondaryAction && (
          <Button variant="outline" size="sm" onClick={secondaryAction.onClick}>
            {secondaryAction.label}
          </Button>
        )}
        {action && (
          <Button size="sm" onClick={action.onClick}>
            {action.label}
          </Button>
        )}
      </div>
    </div>
  );
}

// Pre-built empty states
export function EmptyComponentsState({ onAddComponent }: { onAddComponent?: () => void }) {
  return (
    <EmptyState
      title="컴포넌트가 없습니다"
      description="왼쪽 패널에서 컴포넌트를 추가하거나, AI Copilot에게 '폼을 만들어줘'라고 요청해보세요."
      icon={
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <line x1="9" y1="9" x2="15" y2="9" />
          <line x1="9" y1="13" x2="15" y2="13" />
          <line x1="9" y1="17" x2="12" y2="17" />
        </svg>
      }
      action={onAddComponent ? { label: "컴포넌트 추가", onClick: onAddComponent } : undefined}
    />
  );
}

export function EmptyActionsState({ onAddAction }: { onAddAction?: () => void }) {
  return (
    <EmptyState
      title="액션이 없습니다"
      description="버튼 클릭 시 실행할 동작을 추가하세요. API 호출, 상태 변경 등을 설정할 수 있습니다."
      icon={
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="12" cy="12" r="3" />
          <path d="M12 2v4m0 12v4M2 12h4m12 0h4" />
        </svg>
      }
      action={onAddAction ? { label: "액션 추가", onClick: onAddAction } : undefined}
    />
  );
}

export function EmptyPreviewState() {
  return (
    <EmptyState
      title="미리보기 준비 중"
      description="컴포넌트를 추가하면 여기에 미리보기가 표시됩니다."
      icon={
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      }
    />
  );
}

export function WelcomeState({
  onStartFromTemplate,
  onStartBlank,
}: {
  onStartFromTemplate?: () => void;
  onStartBlank?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="text-6xl mb-4">🎨</div>
      <h2 className="text-2xl font-bold mb-2">새 화면 만들기</h2>
      <p className="text-muted-foreground text-center max-w-md mb-8">
        템플릿으로 빠르게 시작하거나, 빈 화면으로 시작하세요.
      </p>
      <div className="grid grid-cols-2 gap-4 w-full max-w-md">
        <button
          onClick={onStartFromTemplate}
          className="flex flex-col items-center gap-3 p-6 rounded-xl border border-dashed hover:border-primary hover:bg-primary/5 transition-colors"
        >
          <div className="text-3xl">📋</div>
          <div className="text-sm font-medium">템플릿 사용</div>
          <div className="text-xs text-muted-foreground">미리 만들어진 템플릿</div>
        </button>
        <button
          onClick={onStartBlank}
          className="flex flex-col items-center gap-3 p-6 rounded-xl border border-dashed hover:border-primary hover:bg-primary/5 transition-colors"
        >
          <div className="text-3xl">✨</div>
          <div className="text-sm font-medium">빈 화면</div>
          <div className="text-xs text-muted-foreground">직접 처음부터 만들기</div>
        </button>
      </div>
      <div className="mt-8 p-4 bg-muted/50 rounded-lg max-w-md">
        <p className="text-sm text-muted-foreground">
          💡 <strong>팁:</strong> AI Copilot에게 "고객 목록 화면을 만들어줘"라고 요청하면 자동으로 생성해 드립니다.
        </p>
      </div>
    </div>
  );
}