"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface TourStep {
  id: string;
  title: string;
  description: string;
  icon?: string;
  tips?: string[];
}

const TOUR_STEPS: TourStep[] = [
  {
    id: "welcome",
    title: "화면 에디터에 오신 것을 환영합니다! 🎉",
    description: "이 에디터로 대시보드, 폼, 테이블 등 다양한 화면을 쉽게 만들 수 있습니다.",
    tips: ["드래그 앤 드롭으로 컴포넌트 배치", "AI Copilot로 자연어로 화면 구성", "실시간 미리보기로 바로 확인"],
  },
  {
    id: "components",
    title: "컴포넌트 패널 📦",
    description: "왼쪽 패널에서 다양한 컴포넌트를 선택할 수 있습니다.",
    tips: [
      "text, button, input, table, chart 등 지원",
      "컴포넌트를 클릭하여 캔버스에 추가",
      "각 컴포넌트는 고유 ID가 필요",
    ],
  },
  {
    id: "properties",
    title: "속성 패널 ⚙️",
    description: "선택한 컴포넌트의 속성을 편집할 수 있습니다.",
    tips: [
      "label, placeholder, color 등 설정",
      "바인딩으로 동적 데이터 연결",
      "조건부 표시 규칙 설정",
    ],
  },
  {
    id: "actions",
    title: "액션 탭 🎬",
    description: "버튼 클릭 시 실행할 동작을 정의합니다.",
    tips: [
      "API 호출로 서버와 통신",
      "상태 변경으로 화면 업데이트",
      "체인 정책으로 에러 처리",
    ],
  },
  {
    id: "bindings",
    title: "바인딩 탭 🔗",
    description: "컴포넌트와 데이터를 연결합니다.",
    tips: [
      "{{state.field}} - 상태 데이터",
      "{{context.user_id}} - 컨텍스트 데이터",
      "{{inputs.search}} - 입력값",
    ],
  },
  {
    id: "copilot",
    title: "AI Copilot 🤖",
    description: "자연어로 화면을 수정할 수 있습니다.",
    tips: [
      "'버튼을 파란색으로 바꿔줘'라고 입력",
      "'테이블에 페이지네이션 추가' 가능",
      "AI가 JSON Patch로 자동 변환",
    ],
  },
  {
    id: "preview",
    title: "미리보기 & 배포 🚀",
    description: "작성한 화면을 미리보고 배포합니다.",
    tips: [
      "Preview 탭에서 실제 동작 확인",
      "Publish로 운영 환경에 배포",
      "버전 히스토리로 롤백 가능",
    ],
  },
];

const STORAGE_KEY = "screen-editor-onboarding-completed";

interface OnboardingTourProps {
  onComplete?: () => void;
  forceShow?: boolean;
}

export function OnboardingTour({ onComplete, forceShow = false }: OnboardingTourProps) {
  const [isOpen, setIsOpen] = useState(() => {
    const savedCompleted = localStorage.getItem(STORAGE_KEY);
    return !savedCompleted || forceShow;
  });
  const [currentStep, setCurrentStep] = useState(0);

  const handleNext = () => {
    if (currentStep < TOUR_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setIsOpen(false);
    onComplete?.();
  };

  const handleSkip = () => {
    handleComplete();
  };

  const step = TOUR_STEPS[currentStep];
  const isLastStep = currentStep === TOUR_STEPS.length - 1;
  const isFirstStep = currentStep === 0;

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">
            {step.title}
          </DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            {step.description}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {step.tips && step.tips.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">팁:</p>
              <ul className="space-y-1">
                {step.tips.map((tip, index) => (
                  <li
                    key={index}
                    className="text-sm flex items-start gap-2"
                  >
                    <span className="text-primary mt-0.5">•</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Progress indicators */}
        <div className="flex justify-center gap-1.5 pb-2">
          {TOUR_STEPS.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentStep(index)}
              className={`w-2 h-2 rounded-full transition-all ${
                index === currentStep
                  ? "bg-primary w-4"
                  : index < currentStep
                  ? "bg-primary/50"
                  : "bg-muted"
              }`}
              aria-label={`Step ${index + 1}`}
            />
          ))}
        </div>

        <DialogFooter className="flex justify-between sm:justify-between">
          <div className="flex gap-2">
            {!isFirstStep && (
              <Button variant="outline" size="sm" onClick={handlePrevious}>
                이전
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={handleSkip}>
              건너뛰기
            </Button>
          </div>
          <Button size="sm" onClick={handleNext}>
            {isLastStep ? "시작하기" : "다음"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function useOnboardingStatus() {
  const [isCompleted, setIsCompleted] = useState(() => {
    const completed = localStorage.getItem(STORAGE_KEY);
    return !!completed;
  });

  const resetOnboarding = () => {
    localStorage.removeItem(STORAGE_KEY);
    setIsCompleted(false);
  };

  return { isCompleted, resetOnboarding };
}