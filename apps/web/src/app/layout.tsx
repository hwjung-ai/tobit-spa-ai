import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import NavTabs from "../components/NavTabs";
import MobileBottomNav from "../components/MobileBottomNav";
import CepEventBell from "../components/CepEventBell";
import SystemStatusIndicator from "../components/SystemStatusIndicator";
import Providers from "./providers";
import HeaderUserMenu from "../components/HeaderUserMenu";
import ThemeToggle from "../components/ThemeToggle";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Intelligent Ops Studio",
  description: "Streaming chat + document AI powered by OpenAI and pgvector",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  const stored = localStorage.getItem('tobit-theme-preset');
                  const theme = stored && ['light', 'dark', 'brand'].includes(stored) ? stored : 'dark';
                  document.documentElement.setAttribute('data-theme', theme);
                  if (theme === 'dark') {
                    document.documentElement.classList.add('dark');
                  } else {
                    document.documentElement.classList.remove('dark');
                  }
                } catch (e) {
                  console.error('[ThemeInit] Error:', e);
                }
              })();
            `,
          }}
        />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <Providers>
          <div className="min-h-screen">
            <a
              href="#main-content"
              className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-sky-600 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white focus:outline-none focus:ring-2 focus:ring-sky-400"
            >
              Skip to main content
            </a>
            <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4 dark:border-slate-800 dark:bg-slate-950">
                <div className="flex items-end gap-5">
                  <div>
                    <p className="text-xs uppercase tracking-wider text-slate-600 dark:text-slate-400">
                      Tobit SPA AI
                    </p>
                    <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">Intelligent Ops Studio</h1>
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
            <main id="main-content" className="min-h-[calc(100vh-96px)] w-full bg-white px-4 pb-16 pt-4 text-slate-900 md:px-6 md:pb-4 dark:bg-slate-950 dark:text-slate-50">
              {children}
            </main>
            <MobileBottomNav />
          </div>
        </Providers>
      </body>
    </html>
  );
}
