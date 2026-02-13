"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const [email, setEmail] = useState("admin@tobit.local");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email, password);
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-base dark:bg-surface-base">
      <div className="container-panel w-full max-w-md space-y-6">
        <div>
          <h2 className="text-center text-2xl font-semibold text-foreground dark:text-slate-50">
            Tobit SPA AI
          </h2>
          <p className="mt-2 text-center text-sm text-muted-foreground dark:text-muted-foreground">
            Sign in to your account
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Label htmlFor="email" className="w-28 shrink-0 text-foreground dark:text-slate-50">
                Email Address
              </Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="flex-1"
                placeholder="admin@tobit.local"
              />
            </div>

            <div className="flex items-center gap-3">
              <Label htmlFor="password" className="w-28 shrink-0 text-foreground dark:text-slate-50">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="flex-1"
                placeholder="•••••••"
              />
            </div>
          </div>

          {error && (
            <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 dark:bg-rose-900/20 dark:border-rose-800">
              <p className="text-sm text-rose-700 dark:text-rose-300">{error}</p>
            </div>
          )}

          <Button
            type="submit"
            disabled={loading}
            className="w-full"
          >
            {loading ? "Signing in..." : "Sign in"}
          </Button>
        </form>

        <div className="rounded-lg border border-variant bg-surface-base p-4 text-xs text-muted-foreground dark:border-variant dark:bg-surface-base dark:text-muted-foreground">
          <p className="font-semibold mb-2">Demo Credentials:</p>
          <p>Email: admin@tobit.local</p>
          <p>Password: admin123</p>
        </div>
      </div>
    </div>
  );
}
