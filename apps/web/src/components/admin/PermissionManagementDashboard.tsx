"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Search, Plus, Trash2 } from "lucide-react";

interface Permission {
  id: string;
  resource_type: string;
  resource_id?: string;
  permission: string;
  is_granted: boolean;
  expires_at?: string;
}

interface User {
  id: string;
  username: string;
  email?: string;
  role: "admin" | "manager" | "developer" | "viewer";
  is_active: boolean;
}

interface GrantPermissionPayload {
  user_id: string;
  resource_type: string;
  permission: string;
  resource_id?: string;
  expires_at?: string;
}

const PERMISSION_TYPES = [
  { label: "API Management", values: ["api:read", "api:create", "api:update", "api:delete", "api:execute", "api:export"] },
  { label: "CI/CD Management", values: ["ci:read", "ci:create", "ci:update", "ci:delete", "ci:execute", "ci:pause"] },
  { label: "Metrics", values: ["metric:read", "metric:export"] },
  { label: "Graph", values: ["graph:read", "graph:update"] },
  { label: "History & Audit", values: ["history:read", "history:delete", "audit:read", "audit:export"] },
  { label: "CEP Rules", values: ["cep:read", "cep:create", "cep:update", "cep:delete", "cep:execute"] },
  { label: "Documents", values: ["document:read", "document:upload", "document:delete", "document:export"] },
  { label: "UI", values: ["ui:read", "ui:create", "ui:update", "ui:delete"] },
  { label: "Assets", values: ["asset:read", "asset:create", "asset:update", "asset:delete"] },
  { label: "Settings", values: ["settings:read", "settings:update"] },
  { label: "User Management", values: ["user:read", "user:create", "user:update", "user:delete"] },
];

const RESOURCE_TYPES = ["api", "ci", "metric", "graph", "history", "cep", "document", "ui", "asset", "settings", "user"];

export function PermissionManagementDashboard() {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [userPermissions, setUserPermissions] = useState<Permission[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isGrantDialogOpen, setIsGrantDialogOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form states for granting permissions
  const [grantForm, setGrantForm] = useState<GrantPermissionPayload>({
    user_id: "",
    resource_type: "",
    permission: "",
  });

  // Fetch users (mock)
  useEffect(() => {
    const mockUsers: User[] = [
      { id: "user1", username: "john_dev", email: "john@example.com", role: "developer", is_active: true },
      { id: "user2", username: "jane_manager", email: "jane@example.com", role: "manager", is_active: true },
      { id: "user3", username: "admin_user", email: "admin@example.com", role: "admin", is_active: true },
      { id: "user4", username: "viewer_user", email: "viewer@example.com", role: "viewer", is_active: true },
    ];
    setUsers(mockUsers);
  }, []);

  // Fetch user permissions when user is selected
  useEffect(() => {
    if (selectedUser) {
      fetchUserPermissions(selectedUser.id);
    }
  }, [selectedUser]);

  const fetchUserPermissions = async (userId: string) => {
    try {
      setLoading(true);
      // Mock API call - replace with actual API using userId
      console.debug(`Fetching permissions for user: ${userId}`);
      const mockPermissions: Permission[] = [
        { id: "p1", resource_type: "api", permission: "api:read", is_granted: true },
        { id: "p2", resource_type: "api", permission: "api:create", is_granted: true },
        { id: "p3", resource_type: "ci", permission: "ci:read", is_granted: true },
      ];
      setUserPermissions(mockPermissions);
      setError(null);
    } catch {
      setError("Failed to fetch permissions");
    } finally {
      setLoading(false);
    }
  };

  const handleGrantPermission = async () => {
    if (!grantForm.user_id || !grantForm.resource_type || !grantForm.permission) {
      setError("Please fill in all required fields");
      return;
    }

    try {
      setLoading(true);
      // Mock API call
      const newPermission: Permission = {
        id: `p${Date.now()}`,
        ...grantForm,
        is_granted: true,
      };
      setUserPermissions([...userPermissions, newPermission]);
      setSuccess(`Permission granted successfully!`);
      setGrantForm({ user_id: "", resource_type: "", permission: "" });
      setIsGrantDialogOpen(false);
      setTimeout(() => setSuccess(null), 3000);
    } catch {
      setError("Failed to grant permission");
    } finally {
      setLoading(false);
    }
  };

  const handleRevokePermission = async (permissionId: string) => {
    try {
      setLoading(true);
      // Mock API call
      setUserPermissions(userPermissions.filter(p => p.id !== permissionId));
      setSuccess("Permission revoked successfully!");
      setTimeout(() => setSuccess(null), 3000);
    } catch {
      setError("Failed to revoke permission");
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = users.filter(u =>
    u.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
    u.email?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getRoleColor = (role: string) => {
    const colors = {
      admin: "bg-red-100 text-red-800",
      manager: "bg-orange-100 text-orange-800",
      developer: "bg-blue-100 text-blue-800",
      viewer: "bg-gray-100 text-gray-800",
    };
    return colors[role as keyof typeof colors] || "bg-gray-100";
  };

  const getPermissionStatusColor = (isGranted: boolean) => {
    return isGranted ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800";
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Permission Management</CardTitle>
          <CardDescription>Manage user roles and resource-level permissions</CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert className="mb-4 bg-rose-50 border-rose-200 text-rose-800">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {success && (
            <Alert className="mb-4 bg-green-50 border-green-200">
              <AlertDescription className="text-green-800">{success}</AlertDescription>
            </Alert>
          )}

          <Tabs defaultValue="users" className="w-full">
            <TabsList>
              <TabsTrigger value="users">User Management</TabsTrigger>
              <TabsTrigger value="permissions">Permission Matrix</TabsTrigger>
            </TabsList>

            {/* Users Tab */}
            <TabsContent value="users" className="space-y-4 mt-4">
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Search by username or email..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-8"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredUsers.map((user) => (
                  <Card
                    key={user.id}
                    className={`cursor-pointer transition ${
                      selectedUser?.id === user.id ? "border-blue-500 bg-blue-50" : ""
                    }`}
                    onClick={() => setSelectedUser(user)}
                  >
                    <CardContent className="pt-6">
                      <div className="space-y-2">
                        <h3 className="font-semibold">{user.username}</h3>
                        <p className="text-sm text-gray-600">{user.email}</p>
                        <div className="flex items-center gap-2">
                          <Badge className={getRoleColor(user.role)}>{user.role}</Badge>
                          {user.is_active ? (
                            <Badge variant="outline" className="bg-green-50">
                              Active
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="bg-gray-50">
                              Inactive
                            </Badge>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            {/* Permissions Tab */}
            <TabsContent value="permissions" className="space-y-4 mt-4">
              {selectedUser ? (
                <div className="space-y-4">
                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                    <h3 className="font-semibold text-blue-900">
                      Permissions for: {selectedUser.username}
                    </h3>
                    <p className="text-sm text-blue-700 mt-1">
                      Role: <Badge className={getRoleColor(selectedUser.role)}>{selectedUser.role}</Badge>
                    </p>
                  </div>

                  <Dialog open={isGrantDialogOpen} onOpenChange={setIsGrantDialogOpen}>
                    <DialogTrigger onClick={() => setIsGrantDialogOpen(true)}>
                      <Button>
                        <Plus className="w-4 h-4 mr-2" />
                        Grant Permission
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Grant Permission</DialogTitle>
                        <DialogDescription>
                          Grant a new permission to {selectedUser.username}
                        </DialogDescription>
                      </DialogHeader>
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium mb-2">Resource Type</label>
                          <Select
                            value={grantForm.resource_type}
                            onValueChange={(value) =>
                              setGrantForm({ ...grantForm, resource_type: value, permission: "" })
                            }
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select resource type" />
                            </SelectTrigger>
                            <SelectContent>
                              {RESOURCE_TYPES.map((type) => (
                                <SelectItem key={type} value={type}>
                                  {type}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <div>
                          <label className="block text-sm font-medium mb-2">Permission</label>
                          <Select
                            value={grantForm.permission}
                            onValueChange={(value) =>
                              setGrantForm({ ...grantForm, permission: value })
                            }
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select permission" />
                            </SelectTrigger>
                            <SelectContent>
                              {PERMISSION_TYPES.map((group) => (
                                <optgroup key={group.label} label={group.label}>
                                  {group.values.map((perm) => (
                                    <SelectItem key={perm} value={perm}>
                                      {perm}
                                    </SelectItem>
                                  ))}
                                </optgroup>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <div>
                          <label className="block text-sm font-medium mb-2">Resource ID (Optional)</label>
                          <Input
                            placeholder="e.g., api-123 (leave empty for all resources of type)"
                            value={grantForm.resource_id || ""}
                            onChange={(e) =>
                              setGrantForm({ ...grantForm, resource_id: e.target.value || undefined })
                            }
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium mb-2">Expires At (Optional)</label>
                          <Input
                            type="datetime-local"
                            value={grantForm.expires_at || ""}
                            onChange={(e) =>
                              setGrantForm({ ...grantForm, expires_at: e.target.value || undefined })
                            }
                          />
                        </div>

                        <Button onClick={handleGrantPermission} disabled={loading} className="w-full">
                          {loading ? "Granting..." : "Grant Permission"}
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>

                  {/* Permissions List */}
                  <div className="space-y-2">
                    {userPermissions.length > 0 ? (
                      userPermissions.map((perm) => (
                        <Card key={perm.id}>
                          <CardContent className="pt-6">
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <Badge variant="outline">{perm.resource_type}</Badge>
                                  <Badge className={getPermissionStatusColor(perm.is_granted)}>
                                    {perm.permission}
                                  </Badge>
                                  {perm.resource_id && (
                                    <Badge variant="outline" className="text-xs">
                                      {perm.resource_id}
                                    </Badge>
                                  )}
                                </div>
                                {perm.expires_at && (
                                  <p className="text-xs text-gray-600">
                                    Expires: {new Date(perm.expires_at).toLocaleString()}
                                  </p>
                                )}
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleRevokePermission(perm.id)}
                                disabled={loading}
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      ))
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        No permissions assigned yet
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  Select a user from the Users tab to manage their permissions
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Role Hierarchy Reference */}
      <Card>
        <CardHeader>
          <CardTitle>Role Hierarchy Reference</CardTitle>
          <CardDescription>Default permissions by role</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { role: "admin", permissions: 40, description: "All permissions" },
              { role: "manager", permissions: 30, description: "All except user management" },
              { role: "developer", permissions: 18, description: "Create, read, update, execute" },
              { role: "viewer", permissions: 9, description: "Read-only access" },
            ].map((item) => (
              <Card key={item.role}>
                <CardContent className="pt-6">
                  <div className="space-y-2">
                    <Badge className={getRoleColor(item.role)}>{item.role.toUpperCase()}</Badge>
                    <p className="text-sm font-medium">{item.permissions} permissions</p>
                    <p className="text-xs text-gray-600">{item.description}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
