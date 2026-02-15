"use client";

interface Enrichment {
  id: string;
  type: "lookup" | "aggregate" | "ml_model";
  source?: string;
  key?: string;
  outputField?: string;
}

interface EnrichmentSectionProps {
  enrichments: Enrichment[];
  onEnrichmentsChange: (enrichments: Enrichment[]) => void;
}

const ENRICHMENT_TYPES = [
  {
    value: "lookup" as const,
    label: "데이터 조회",
    description: "외부 데이터 소스에서 데이터 조회",
  },
  {
    value: "aggregate" as const,
    label: "집계 데이터",
    description: "과거 집계 데이터 추가",
  },
  {
    value: "ml_model" as const,
    label: "ML 모델",
    description: "머신러닝 모델 적용",
  },
];

export function EnrichmentSection({
  enrichments,
  onEnrichmentsChange,
}: EnrichmentSectionProps) {
  const addEnrichment = () => {
    const newEnrichment: Enrichment = {
      id: `enrich-${Date.now()}`,
      type: "lookup",
      source: "",
      key: "",
      outputField: "",
    };
    onEnrichmentsChange([...enrichments, newEnrichment]);
  };

  const removeEnrichment = (id: string) => {
    onEnrichmentsChange(enrichments.filter((e) => e.id !== id));
  };

  const updateEnrichment = (id: string, updates: Partial<Enrichment>) => {
    onEnrichmentsChange(
      enrichments.map((e) => (e.id === id ? { ...e, ...updates } : e))
    );
  };

  return (
    <div className="cep-section-container">
      <div className="cep-section-header">
        <h3 className="cep-section-title">
          데이터 보강 (선택사항)
        </h3>
        <span className="cep-section-counter">{enrichments.length}개</span>
      </div>
      <p className="cep-text-muted">
        외부 데이터나 머신러닝 결과를 이벤트에 추가합니다
      </p>

      {enrichments.length === 0 ? (
        <div className="cep-empty-state">
          <p className="cep-empty-state-text">데이터 보강을 추가해주세요</p>
        </div>
      ) : (
        <div className="space-y-3">
          {enrichments.map((enrichment) => (
            <div
              key={enrichment.id}
              className="cep-item-card"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex-1">
                  <label className="cep-window-label">타입</label>
                  <select
                    value={enrichment.type}
                    onChange={(e) =>
                      updateEnrichment(enrichment.id, {
                        type: e.target.value as "lookup" | "aggregate" | "ml_model",
                      })
                    }
                    className="cep-select w-full mt-1"
                  >
                    {ENRICHMENT_TYPES.map((et) => (
                      <option key={et.value} value={et.value}>
                        {et.label}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={() => removeEnrichment(enrichment.id)}
                  className="rounded-lg border border-rose-500/50 bg-rose-500/10 px-2 py-1 text-xs text-rose-400 hover:bg-rose-500/20 mt-5"
                >
                  삭제
                </button>
              </div>

              {enrichment.type === "lookup" && (
                <>
                  <input
                    type="text"
                    value={enrichment.source || ""}
                    onChange={(e) =>
                      updateEnrichment(enrichment.id, {
                        source: e.target.value,
                      })
                    }
                    placeholder="데이터 소스 (예: Redis key)"
                    className="cep-input-full"
                  />
                  <input
                    type="text"
                    value={enrichment.key || ""}
                    onChange={(e) =>
                      updateEnrichment(enrichment.id, {
                        key: e.target.value,
                      })
                    }
                    placeholder="조회 키 (예: user_id)"
                    className="cep-input-full"
                  />
                </>
              )}

              {enrichment.type === "aggregate" && (
                <input
                  type="text"
                  value={enrichment.source || ""}
                  onChange={(e) =>
                    updateEnrichment(enrichment.id, {
                      source: e.target.value,
                    })
                  }
                  placeholder="집계 기간 (예: 1h, 24h)"
                  className="cep-select-primary w-full"
                />
              )}

              {enrichment.type === "ml_model" && (
                <input
                  type="text"
                  value={enrichment.source || ""}
                  onChange={(e) =>
                    updateEnrichment(enrichment.id, {
                      source: e.target.value,
                    })
                  }
                  placeholder="모델명 (예: anomaly_detection_v1)"
                  className="cep-select-primary w-full"
                />
              )}

              <input
                type="text"
                value={enrichment.outputField || ""}
                onChange={(e) =>
                  updateEnrichment(enrichment.id, {
                    outputField: e.target.value,
                  })
                }
                placeholder="출력 필드명 (예: user_name)"
                className="cep-select-primary w-full"
              />
            </div>
          ))}
        </div>
      )}

      <button
        onClick={addEnrichment}
        className="w-full rounded-lg border border-cyan-500/50 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-400 hover:bg-cyan-500/20"
      >
        + 보강 추가
      </button>
    </div>
  );
}
