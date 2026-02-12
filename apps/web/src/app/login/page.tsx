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
    <div className="flex min-h-screen items-center justify-center" style={{ backgroundColor: "var(--background)" }}>
      <div
        className="w-full max-w-md space-y-6 rounded-2xl border p-6 shadow-sm"
        style={{ backgroundColor: "var(--surface-base)", borderColor: "var(--border)" }}
      >
        <div>
          <h2 className="text-center text-2xl font-semibold" style={{ color: "var(--foreground)" }}>
            Tobit SPA AI
          </h2>
          <p className="mt-2 text-center text-sm" style={{ color: "var(--muted-foreground)" }}>
            Sign in to your account
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <div className="space-y-4">
            <div>
              <Label htmlFor="email" style={{ color: "var(--foreground)" }}>
                Email Address
              </Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="mt-1"
                placeholder="admin@tobit.local"
              />
            </div>

            <div>
              <Label htmlFor="password" style={{ color: "var(--foreground)" }}>
                Password
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="mt-1"
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

        <div
          className="rounded-lg border p-4 text-xs"
          style={{ backgroundColor: "var(--surface-base)", color: "var(--muted-foreground)", borderColor: "var(--border)" }}
        >
          <p className="font-semibold mb-2">Demo Credentials:</p>
          <p>Email: admin@tobit.local</p>
          <p>Password: admin123</p>
        </div>
      </div>
    </div>
  );
}
