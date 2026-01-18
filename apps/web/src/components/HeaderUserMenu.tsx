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
    return <div className="h-10 w-24 bg-slate-800 rounded animate-pulse" />;
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
        return "text-red-400";
      case "manager":
        return "text-orange-400";
      case "developer":
        return "text-blue-400";
      default:
        return "text-slate-400";
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white"
        >
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center">
              <span className="text-xs font-bold">
                {user.username.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="text-left">
              <div className="text-xs font-medium">{user.username}</div>
              <div className={`text-xs ${getRoleColor(user.role)}`}>
                {user.role}
              </div>
            </div>
          </div>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="bg-slate-900 border-slate-700">
        <DropdownMenuLabel className="text-slate-300">
          <div className="flex flex-col gap-1">
            <div className="font-semibold">{user.username}</div>
            <div className="text-xs text-slate-400">{user.email}</div>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator className="bg-slate-700" />
        <DropdownMenuItem
          onClick={handleLogout}
          className="text-slate-300 hover:bg-slate-800 cursor-pointer"
        >
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
