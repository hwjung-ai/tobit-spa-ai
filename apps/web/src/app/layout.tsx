import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import NavTabs from "../components/NavTabs";
import CepEventBell from "../components/CepEventBell";
import SystemStatusIndicator from "../components/SystemStatusIndicator";
import Providers from "./providers";
import HeaderUserMenu from "../components/HeaderUserMenu";

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
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <Providers>
          <div className="min-h-screen bg-slate-950 text-slate-100">
            <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
                <div className="flex items-end gap-5">
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
                      Tobit SPA AI
                    </p>
                    <h1 className="text-2xl font-semibold text-white">Intelligent Ops Studio</h1>
                  </div>
                  <SystemStatusIndicator />
                </div>
              <nav className="flex items-center gap-6">
                <CepEventBell />
                <NavTabs />
                <HeaderUserMenu />
              </nav>
            </header>
            <main className="min-h-[calc(100vh-96px)] w-full px-4 py-4 md:px-6">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
