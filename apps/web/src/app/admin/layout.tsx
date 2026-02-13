"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared";

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();

    const tabs = [
        { label: "Assets", href: "/admin/assets" },
        { label: "Tools", href: "/admin/tools" },
        { label: "Catalogs", href: "/admin/catalogs" },
        { label: "Screens", href: "/admin/screens" },
        { label: "Explorer", href: "/admin/explorer" },
        { label: "Settings", href: "/admin/settings" },
        { label: "Inspector", href: "/admin/inspector" },
        { label: "Regression", href: "/admin/regression" },
        { label: "Observability", href: "/admin/observability" },
        { label: "Logs", href: "/admin/logs" },
    ];

    const getTabDescription = () => {
        if (pathname.startsWith("/admin/assets")) return "자산 레지스트리에서 프롬프트, 매핑, 정책, 쿼리, 소스, 리졸버를 관리합니다.";
        if (pathname.startsWith("/admin/tools")) return "도구 자산을 조회하고 실행 구성을 검증합니다.";
        if (pathname.startsWith("/admin/catalogs")) return "데이터베이스 카탈로그를 스캔하고 스키마 정보를 관리합니다.";
        if (pathname.startsWith("/admin/screens")) return "UI Screen 자산을 생성, 편집, 게시, 롤백합니다.";
        if (pathname.startsWith("/admin/explorer")) return "읽기 전용 탐색기로 Postgres, Neo4j, Redis 데이터를 조회합니다.";
        if (pathname.startsWith("/admin/settings")) return "운영 설정, LLM 구성, 런타임 API 인증 정책을 관리합니다.";
        if (pathname.startsWith("/admin/inspector")) return "실행 기록을 trace_id 기준으로 조회하고 자산 적용 상태를 점검합니다.";
        if (pathname.startsWith("/admin/regression")) return "회귀 감시 규칙을 운영하고 변경 영향도를 추적합니다.";
        if (pathname.startsWith("/admin/observability")) return "시스템/CEP 관측 지표와 알림 현황을 모니터링합니다.";
        if (pathname.startsWith("/admin/logs")) return "쿼리, 실행 추적, 감사, LLM 호출 및 서버 로그를 조회합니다.";
        return "관리 기능을 선택해 운영 상태를 점검하세요.";
    };

    return (
        <div className="tracking-tight builder-shell builder-text text-foreground">
            <PageHeader
                title="Adminstrator"
                description="운영 파라미터를 설정하고 핵심 자산을 관리하며 시스템 활동을 점검합니다."
                actions={<div className="text-label-sm">시스템 관리</div>}
            />

            {/* Sub Navigation (Capsule Style like Data page) */}
            <div className="mb-6 mt-6 flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                    {tabs.map((tab) => {
                        const isActive = pathname.startsWith(tab.href);
                        return (
                            <Link
                                key={tab.label}
                                href={tab.href}
                                className={cn(
                                    "rounded-full border px-4 py-1.5 text-xs font-bold uppercase tracking-wider transition",
                                    isActive
                                        ? "border-sky-600 bg-sky-600 text-white dark:border-sky-700 dark:bg-sky-700"
                                        : "border-slate-300 text-slate-700 hover:border-sky-500 hover:bg-sky-50 hover:text-sky-700 dark:border-slate-700 dark:text-slate-300 dark:hover:border-sky-500 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                                )}
                            >
                                {tab.label}
                            </Link>
                        );
                    })}
                </div>
            </div>
            <p className="mb-6 text-sm text-muted-standard">{getTabDescription()}</p>

            {/* Main Content Area */}
            <div className="animate-in fade-in duration-700">
                {children}
            </div>
        </div>
    );
}
