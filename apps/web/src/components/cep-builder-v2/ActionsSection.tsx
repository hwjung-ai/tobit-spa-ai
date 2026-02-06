"use client";

import { useState } from "react";
import { FormFieldGroup } from "./FormFieldGroup";

interface Action {
  id: string;
  type: "webhook" | "notify" | "trigger" | "store";
  endpoint?: string;
  method?: "GET" | "POST" | "PUT" | "DELETE";
  channels?: string[];
  message?: string;
}

interface ActionsSectionProps {
  actions: Action[];
  onActionsChange: (actions: Action[]) => void;
  onAiGenerate?: () => void;
}

const ACTION_TYPES = [
  { value: "webhook", label: "Webhook 호출" },
  { value: "notify", label: "알림 전송" },
  { value: "trigger", label: "규칙 실행" },
  { value: "store", label: "데이터 저장" },
];

const CHANNELS = ["Slack", "Email", "SMS", "Discord"];

export function ActionsSection({
  actions,
  onActionsChange,
  onAiGenerate,
}: ActionsSectionProps) {
  const addAction = () => {
    const newAction: Action = {
      id: `action-${Date.now()}`,
      type: "webhook",
      endpoint: "",
      method: "POST",
    };
    onActionsChange([...actions, newAction]);
  };

  const removeAction = (id: string) => {
    onActionsChange(actions.filter((a) => a.id !== id));
  };

  const updateAction = (id: string, updates: Partial<Action>) => {
    onActionsChange(actions.map((a) => (a.id === id ? { ...a, ...updates } : a)));
  };

  return (
    <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">액션 설정 (필수)</h3>
        <span className="text-xs text-slate-500">{actions.length}개</span>
      </div>

      {actions.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/20 py-6 text-center">
          <p className="text-xs text-slate-400">액션을 추가해주세요</p>
        </div>
      ) : (
        <div className="space-y-3">
          {actions.map((action) => (
            <div
              key={action.id}
              className="rounded-lg border border-slate-700 bg-slate-900/40 p-3 space-y-3"
            >
              <div className="flex items-center justify-between">
                <select
                  value={action.type}
                  onChange={(e) =>
                    updateAction(action.id, {
                      type: e.target.value as any,
                    })
                  }
                  className="rounded-lg border border-slate-700 bg-slate-900/60 px-2 py-1 text-xs text-white"
                >
                  {ACTION_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => removeAction(action.id)}
                  className="rounded-lg border border-rose-500/50 bg-rose-500/10 px-2 py-1 text-xs text-rose-400 hover:bg-rose-500/20"
                >
                  삭제
                </button>
              </div>

              {action.type === "webhook" && (
                <>
                  <input
                    type="text"
                    value={action.endpoint || ""}
                    onChange={(e) =>
                      updateAction(action.id, { endpoint: e.target.value })
                    }
                    placeholder="엔드포인트 URL"
                    className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-2 py-1 text-xs text-white placeholder-slate-500"
                  />
                  <select
                    value={action.method || "POST"}
                    onChange={(e) =>
                      updateAction(action.id, {
                        method: e.target.value as any,
                      })
                    }
                    className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-2 py-1 text-xs text-white"
                  >
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="DELETE">DELETE</option>
                  </select>
                </>
              )}

              {action.type === "notify" && (
                <>
                  <input
                    type="text"
                    value={action.message || ""}
                    onChange={(e) =>
                      updateAction(action.id, { message: e.target.value })
                    }
                    placeholder="알림 메시지"
                    className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-2 py-1 text-xs text-white placeholder-slate-500"
                  />
                  <div className="flex flex-wrap gap-2">
                    {CHANNELS.map((channel) => (
                      <label
                        key={channel}
                        className="flex items-center gap-1 text-xs text-slate-300"
                      >
                        <input
                          type="checkbox"
                          defaultChecked={action.channels?.includes(channel)}
                          onChange={(e) => {
                            const channels = action.channels || [];
                            if (e.target.checked) {
                              if (!channels.includes(channel)) {
                                updateAction(action.id, {
                                  channels: [...channels, channel],
                                });
                              }
                            } else {
                              updateAction(action.id, {
                                channels: channels.filter((c) => c !== channel),
                              });
                            }
                          }}
                          className="rounded"
                        />
                        {channel}
                      </label>
                    ))}
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={addAction}
          className="flex-1 rounded-lg border border-emerald-500/50 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-400 hover:bg-emerald-500/20"
        >
          + 액션 추가
        </button>
        {onAiGenerate && (
          <button
            onClick={onAiGenerate}
            className="flex-1 rounded-lg border border-purple-500/50 bg-purple-500/10 px-3 py-2 text-xs font-semibold text-purple-400 hover:bg-purple-500/20"
          >
            🤖 AI 생성
          </button>
        )}
      </div>
    </div>
  );
}
