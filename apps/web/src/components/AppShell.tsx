"use client";

import { usePathname } from "next/navigation";
import NavTabs from "./NavTabs";
import MobileBottomNav from "./MobileBottomNav";
import CepEventBell from "./CepEventBell";
import SystemStatusIndicator from "./SystemStatusIndicator";
import HeaderUserMenu from "./HeaderUserMenu";
import ThemeToggle from "./ThemeToggle";

interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const isLoginPage = pathname === "/login";
  const isViewerPage =
    pathname === "/pdf-viewer" ||
    Boolean(pathname?.startsWith("/documents/") && pathname?.endsWith("/viewer"));
  const hideChrome = isLoginPage || isViewerPage;

  return (
    <div className="min-h-screen">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-sky-600 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white focus:outline-none focus:ring-2 focus:ring-sky-400"
      >
        Skip to main content
      </a>

      {!hideChrome && (
        <header className="flex items-center justify-between border-b border-variant bg-surface-base px-6 py-4 dark:border-variant dark:bg-surface-base">
          <div className="flex items-end gap-5">
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground dark:text-muted-foreground">
                Tobit SPA AI
              </p>
              <h1 className="text-2xl font-semibold text-foreground dark:text-slate-50">Intelligent Ops Studio</h1>
            </div>
            <SystemStatusIndicator />
          </div>
          <nav className="flex items-center gap-6">
            <CepEventBell />
            <ThemeToggle />
            <div className="hidden md:block">
              <NavTabs />
            </div>
            <HeaderUserMenu />
          </nav>
        </header>
      )}

      <main
        id="main-content"
        className={
          hideChrome
            ? "min-h-screen w-full bg-surface-base text-foreground dark:bg-surface-base dark:text-slate-50"
            : "min-h-[calc(100vh-96px)] w-full bg-surface-base px-4 pb-16 pt-4 text-foreground md:px-6 md:pb-4 dark:bg-surface-base dark:text-slate-50"
        }
      >
        {children}
      </main>

      {!hideChrome && <MobileBottomNav />}
    </div>
  );
}
