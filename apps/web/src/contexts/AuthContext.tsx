"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

interface User {
  id: string;
  email: string;
  username: string;
  role: string;
  tenant_id: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Build URL for API requests - empty string means use relative paths (Next.js rewrites proxy)
const buildAuthUrl = (endpoint: string): string => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
  if (!baseUrl) {
    return endpoint;
  }
  return `${baseUrl.replace(/\/+$/, "")}${endpoint}`;
};

const ENABLE_AUTH = process.env.NEXT_PUBLIC_ENABLE_AUTH === "true";
const DEFAULT_TENANT_ID = process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || "default";

function normalizeTenantId(rawTenantId: string | null): string {
  if (!rawTenantId || rawTenantId === "t1") {
    return DEFAULT_TENANT_ID;
  }
  return rawTenantId;
}

// Default debug user for development mode
const DEBUG_USER: User = {
  id: "default",
  email: "debug@dev",
  username: "debug@dev",
  role: "ADMIN",
  tenant_id: DEFAULT_TENANT_ID,
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (user) {
      localStorage.setItem("user_id", user.id);
      localStorage.setItem("tenant_id", user.tenant_id);
    } else {
      localStorage.removeItem("user_id");
      localStorage.removeItem("tenant_id");
    }
  }, [user]);

  // Check for existing token on mount
  useEffect(() => {
    const savedTenantId = localStorage.getItem("tenant_id");
    const normalizedTenantId = normalizeTenantId(savedTenantId);
    if (savedTenantId !== normalizedTenantId) {
      localStorage.setItem("tenant_id", normalizedTenantId);
    }

    // If authentication is disabled, auto-login with debug user
    if (!ENABLE_AUTH) {
      setUser(DEBUG_USER);
      localStorage.setItem("user_id", DEBUG_USER.id);
      localStorage.setItem("tenant_id", normalizeTenantId(DEBUG_USER.tenant_id));
      setIsLoading(false);
      return;
    }

    const token = localStorage.getItem("access_token");
    if (token) {
      fetchCurrentUser();
    } else {
      setIsLoading(false);
    }
  }, []);

  async function fetchCurrentUser() {
    try {
      const url = buildAuthUrl("/auth/me");
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        const tenantId = normalizeTenantId(data.data.user.tenant_id);
        setUser(data.data.user);
        localStorage.setItem("user_id", data.data.user.id);
        localStorage.setItem("tenant_id", tenantId);
      } else {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user_id");
        localStorage.removeItem("tenant_id");
        setUser(null);
      }
    } catch (error) {
      console.error("Failed to fetch user:", error);
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }

  async function login(email: string, password: string) {
    // If authentication is disabled, skip login
    if (!ENABLE_AUTH) {
      setUser(DEBUG_USER);
      return;
    }

    const url = buildAuthUrl("/auth/login");
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || "Login failed");
    }

    const data = await response.json();
    const tenantId = normalizeTenantId(data.data.user.tenant_id);
    localStorage.setItem("access_token", data.data.access_token);
    localStorage.setItem("refresh_token", data.data.refresh_token);
    localStorage.setItem("user_id", data.data.user.id);
    localStorage.setItem("tenant_id", tenantId);
    setUser({ ...data.data.user, tenant_id: tenantId });
  }

  async function logout() {
    try {
      const url = buildAuthUrl("/auth/logout");
      await fetch(url, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
    } catch (error) {
      console.error("Logout error:", error);
    }

    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("tenant_id");
    setUser(null);
  }

  async function refreshToken() {
    const refresh_token = localStorage.getItem("refresh_token");
    if (!refresh_token) throw new Error("No refresh token");

    const url = buildAuthUrl("/auth/refresh");
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token }),
    });

    if (!response.ok) throw new Error("Token refresh failed");

    const data = await response.json();
    localStorage.setItem("access_token", data.data.access_token);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
