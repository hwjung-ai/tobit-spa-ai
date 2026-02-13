"use client";

import { useState, useEffect, useMemo } from "react";
import { cn } from "@/lib/utils";
import { SCREEN_TEMPLATES, ScreenTemplate } from "@/lib/ui-screen/screen-templates";
import { fetchApi } from "@/lib/adminUtils";
import { ScreenSchemaV1 } from "@/lib/ui-screen/screen.schema";

interface TemplateGalleryProps {
  onSelect: (schema: ScreenSchemaV1) => void;
  onClose: () => void;
}

interface PublishedScreen {
  asset_id: string;
  name: string;
  description?: string;
  screen_id?: string;
  tags?: Record<string, unknown>;
  status: string;
  version: number;
  created_by?: string;
  updated_at?: string;
  schema_json?: ScreenSchemaV1;
}

type TabId = "builtin" | "published";

export default function TemplateGallery({ onSelect, onClose }: TemplateGalleryProps) {
  const [activeTab, setActiveTab] = useState<TabId>("builtin");
  const [publishedScreens, setPublishedScreens] = useState<PublishedScreen[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  useEffect(() => {
    if (activeTab === "published") {
      loadPublishedScreens();
    }
  }, [activeTab]);

  const loadPublishedScreens = async () => {
    setLoading(true);
    try {
      const res = await fetchApi("/asset-registry/assets?asset_type=screen&status=published");
      const resData = res as unknown as Record<string, unknown> | undefined;
      const innerData = resData?.data as Record<string, unknown> | undefined;
      const data = (innerData?.assets as PublishedScreen[]) || [];
      setPublishedScreens(data);
    } catch {
      setPublishedScreens([]);
    } finally {
      setLoading(false);
    }
  };

  const allTags = useMemo(() => {
    const tags = new Set<string>();
    publishedScreens.forEach((s) => {
      if (s.tags && typeof s.tags === "object") {
        Object.keys(s.tags).forEach((k) => tags.add(k));
      }
    });
    return Array.from(tags);
  }, [publishedScreens]);

  const filteredPublished = useMemo(() => {
    let filtered = publishedScreens;
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (s) =>
          s.name?.toLowerCase().includes(term) ||
          s.description?.toLowerCase().includes(term) ||
          s.screen_id?.toLowerCase().includes(term)
      );
    }
    if (selectedTag) {
      filtered = filtered.filter(
        (s) => s.tags && typeof s.tags === "object" && selectedTag in s.tags
      );
    }
    return filtered;
  }, [publishedScreens, searchTerm, selectedTag]);

  const filteredBuiltin = useMemo(() => {
    if (!searchTerm.trim()) return SCREEN_TEMPLATES;
    const term = searchTerm.toLowerCase();
    return SCREEN_TEMPLATES.filter(
      (t) =>
        t.name.toLowerCase().includes(term) ||
        t.description.toLowerCase().includes(term)
    );
  }, [searchTerm]);

  const handleSelectBuiltin = (template: ScreenTemplate) => {
    const screenId = `screen_${Date.now()}`;
    const schema = template.generate({ screen_id: screenId, name: template.name });
    onSelect(schema);
  };

  const handleSelectPublished = async (screen: PublishedScreen) => {
    try {
      const res = await fetchApi(`/asset-registry/assets/${screen.asset_id}`);
      const resData = res as unknown as Record<string, unknown> | undefined;
      const innerData = resData?.data as Record<string, unknown> | undefined;
      const asset = innerData?.asset as Record<string, unknown> | undefined;
      if (asset?.schema_json) {
        const cloned: ScreenSchemaV1 = JSON.parse(JSON.stringify(asset.schema_json));
        cloned.id = `screen_${Date.now()}`;
        cloned.screen_id = cloned.id;
        cloned.name = `${cloned.name} (Copy)`;
        onSelect(cloned);
      }
    } catch {
      // Fallback: use what we have
      if (screen.schema_json) {
        const cloned: ScreenSchemaV1 = JSON.parse(JSON.stringify(screen.schema_json));
        cloned.id = `screen_${Date.now()}`;
        cloned.screen_id = cloned.id;
        cloned.name = `${cloned.name} (Copy)`;
        onSelect(cloned);
      }
    }
  };

  const layoutIcons: Record<string, string> = {
    form: "list",
    dashboard: "grid-2x2",
    readonly_detail: "file-text",
    list_filter: "search",
    list_modal_crud: "layers",
    observability_dashboard: "activity",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="border border-variant bg-surface-base rounded-xl w-[720px] max-h-[80vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-variant px-6 py-4">
          <h2 className="text-lg font-semibold text-foreground">
            Template Gallery
          </h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors text-xl leading-none"
          >
            &times;
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-variant px-6">
          {(
            [
              { id: "builtin" as TabId, label: "Built-in Templates" },
              { id: "published" as TabId, label: "Published Screens" },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px",
                activeTab === tab.id
                  ? "border-sky-500 text-sky-400"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search + Filter */}
        <div className="px-6 py-3 flex gap-3 items-center">
          <input
            type="text"
            placeholder="Search templates..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 border border-variant bg-surface-elevated text-foreground-secondary rounded px-3 py-1.5 text-sm placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
          {activeTab === "published" && allTags.length > 0 && (
            <select
              value={selectedTag || ""}
              onChange={(e) => setSelectedTag(e.target.value || null)}
              className="border border-variant bg-surface-elevated text-foreground-secondary rounded px-3 py-1.5 text-sm"
            >
              <option value="">All Tags</option>
              {allTags.map((tag) => (
                <option key={tag} value={tag}>
                  {tag}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 pb-6">
          {activeTab === "builtin" && (
            <div className="grid grid-cols-2 gap-4">
              {filteredBuiltin.map((template) => (
                <button
                  key={template.id}
                  onClick={() => handleSelectBuiltin(template)}
                  className="text-left border border-variant bg-surface-overlay rounded-lg p-4 hover:border-sky-500/50 hover:bg-surface-elevated transition-all group"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded bg-surface-elevated flex items-center justify-center text-sky-400 text-xs font-bold uppercase shrink-0 group-hover:bg-sky-950/50">
                      {layoutIcons[template.id]
                        ? template.id.slice(0, 2).toUpperCase()
                        : "T"}
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-foreground-secondary group-hover:text-sky-300 truncate">
                        {template.name}
                      </h3>
                      <p className="text-xs mt-1 text-muted-foreground line-clamp-2">
                        {template.description}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
              {filteredBuiltin.length === 0 && (
                <div className="col-span-2 py-8 text-center text-foreground text-sm">
                  No templates match your search
                </div>
              )}
            </div>
          )}

          {activeTab === "published" && loading && (
            <div className="flex items-center justify-center py-12">
              <div className="text-sm text-muted-foreground">Loading published screens...</div>
            </div>
          )}

          {activeTab === "published" && !loading && (
            <div className="grid grid-cols-2 gap-4">
              {filteredPublished.map((screen) => (
                <button
                  key={screen.asset_id}
                  onClick={() => handleSelectPublished(screen)}
                  className="text-left border border-variant bg-surface-overlay rounded-lg p-4 hover:border-sky-500/50 hover:bg-surface-elevated transition-all group"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded bg-emerald-950/50 border border-emerald-800/50 flex items-center justify-center text-emerald-400 text-xs font-bold uppercase shrink-0">
                      v{screen.version}
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-foreground-secondary group-hover:text-sky-300 truncate">
                        {screen.name}
                      </h3>
                      <p className="text-xs mt-1 text-muted-foreground line-clamp-2">
                        {screen.description || screen.screen_id || "No description"}
                      </p>
                      {screen.tags && Object.keys(screen.tags).length > 0 && (
                        <div className="flex gap-1 mt-2 flex-wrap">
                          {Object.keys(screen.tags)
                            .slice(0, 3)
                            .map((tag) => (
                              <span
                                key={tag}
                                className="inline-flex px-1.5 py-0.5 rounded text-xs border border-variant bg-surface-elevated text-muted-foreground"
                              >
                                {tag}
                              </span>
                            ))}
                        </div>
                      )}
                    </div>
                  </div>
                </button>
              ))}
              {filteredPublished.length === 0 && (
                <div className="col-span-2 py-8 text-center text-foreground text-sm">
                  {publishedScreens.length === 0
                    ? "No published screens available as templates"
                    : "No screens match your search"}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
