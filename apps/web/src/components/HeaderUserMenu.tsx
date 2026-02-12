"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";

export default function HeaderUserMenu() {
  const { user, isAuthenticated, logout, isLoading } = useAuth();
  const router = useRouter();

  if (isLoading) {
    return <div className="h-10 w-24 rounded animate-pulse" style={{backgroundColor: "var(--surface-elevated)"}} />;
  }

  if (!isAuthenticated || !user) {
    return null;
  }

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case "admin":
        return "#f87171"; // red-400
      case "manager":
        return "#fb923c"; // orange-400
      case "developer":
        return "#60a5fa"; // blue-400
      default:
        return "var(--muted-foreground)";
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="border transition"
          style={{backgroundColor: "var(--surface-elevated)", color: "var(--foreground)", borderColor: "var(--border)"}}
        >
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{backgroundColor: "var(--surface-elevated)"}}>
              <span className="text-xs font-bold">
                {user.username.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="text-left">
              <div className="text-xs font-medium">{user.username}</div>
              <div className="text-xs" style={{color: getRoleColor(user.role)}}>
                {user.role}
              </div>
            </div>
          </div>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="border" style={{backgroundColor: "var(--surface-elevated)", borderColor: "var(--border)"}}>
        <DropdownMenuLabel style={{color: "var(--foreground)"}}>
          <div className="flex flex-col gap-1">
            <div className="font-semibold">{user.username}</div>
            <div className="text-xs" style={{color: "var(--muted-foreground)"}}>{user.email}</div>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator style={{backgroundColor: "var(--border)"}} />
        <DropdownMenuItem
          onClick={handleLogout}
          className="cursor-pointer"
          style={{color: "var(--foreground)"}}
        >
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
