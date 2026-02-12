/**
 * User Permissions Management Panel
 * Manage user permissions and view audit logs
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, Shield, Clock } from 'lucide-react';

interface UserPermission {
  permission: string;
  granted_at?: string;
}

interface User {
  username: string;
  email: string;
  is_active: boolean;
  login_count: number;
  last_login: string | null;
  created_at: string;
}

interface AuditLog {
  user_id: string;
  admin_id: string;
  action: 'grant' | 'revoke';
  permission: string;
  reason?: string;
  created_at: string;
}

interface UserPermissionsPanelProps {
  userId?: string;
}

const UserPermissionsPanel: React.FC<UserPermissionsPanelProps> = ({ userId }) => {
  const [user, setUser] = useState<User | null>(null);
  const [permissions, setPermissions] = useState<UserPermission[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [newPermission, setNewPermission] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'permissions' | 'audit'>('permissions');

  const availablePermissions = [
    'view_dashboard',
    'manage_users',
    'manage_settings',
    'view_logs',
    'manage_rules',
    'manage_api_keys',
    'export_data',
    'create_backups',
  ];

  const fetchUserDetails = useCallback(async () => {
    if (!userId) return;

    setLoading(true);
    try {
      const [userRes, auditRes] = await Promise.all([
        fetch(`/admin/users/${userId}`),
        fetch(`/admin/users/${userId}/audit-log`),
      ]);

      if (userRes.ok) {
        const data = await userRes.json();
        setUser(data.user);
        setPermissions(data.permissions.map((p: string) => ({ permission: p })) || []);
      }

      if (auditRes.ok) {
        const data = await auditRes.json();
        setAuditLogs(data.logs || []);
      }
    } catch (error) {
      console.error('Failed to fetch user details:', error);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (userId) {
      fetchUserDetails();
    }
  }, [userId, fetchUserDetails]);

  const handleGrantPermission = async () => {
    if (!newPermission || !userId) return;

    try {
      const response = await fetch(`/admin/users/${userId}/permissions/grant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          permission: newPermission,
          reason: reason || undefined,
        }),
      });

      if (response.ok) {
        setNewPermission('');
        setReason('');
        await fetchUserDetails();
      }
    } catch (error) {
      console.error('Failed to grant permission:', error);
    }
  };

  const handleRevokePermission = async (permission: string) => {
    if (!userId) return;

    try {
      const response = await fetch(`/admin/users/${userId}/permissions/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          permission,
          reason: 'Revoked via admin dashboard',
        }),
      });

      if (response.ok) {
        await fetchUserDetails();
      }
    } catch (error) {
      console.error('Failed to revoke permission:', error);
    }
  };

  if (!userId) {
    return (
      <div className="bg-white dark:bg-slate-900 rounded-lg border dark:border-slate-700 p-8 text-center">
        <p className="" style={{color: "var(--muted-foreground)"}}>Select a user to manage permissions</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-white dark:bg-slate-900 rounded-lg border dark:border-slate-700 p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600 mx-auto"></div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="bg-white dark:bg-slate-900 rounded-lg border dark:border-slate-700 p-8 text-center">
        <p className="" style={{color: "var(--muted-foreground)"}}>User not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* User Header */}
      <div className="bg-white dark:bg-slate-900 rounded-lg border dark:border-slate-700 p-6">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 bg-sky-100 rounded-full flex items-center justify-center">
            <span className="text-xl font-semibold text-sky-600">
              {user.username.charAt(0).toUpperCase()}
            </span>
          </div>
          <div>
            <h2 className="text-xl font-bold " style={{color: "var(--foreground)"}}>{user.username}</h2>
            <p className="" style={{color: "var(--muted-foreground)"}}>{user.email}</p>
          </div>
          <div className="ml-auto">
            <span
              className={`px-3 py-1 rounded-full text-sm font-semibold ${
                user.is_active
                  ? 'bg-green-100 text-green-800'
                  : 'bg-red-100 text-red-800'
              }`}
            >
              {user.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="" style={{color: "var(--muted-foreground)"}}>Login Count</p>
            <p className="text-lg font-semibold">{user.login_count}</p>
          </div>
          <div>
            <p className="" style={{color: "var(--muted-foreground)"}}>Last Login</p>
            <p className="text-sm font-semibold">
              {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
            </p>
          </div>
          <div>
            <p className="" style={{color: "var(--muted-foreground)"}}>Created</p>
            <p className="text-sm font-semibold">
              {new Date(user.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b dark:border-slate-700 bg-white dark:bg-slate-900 rounded-t-lg">
        <button
          onClick={() => setActiveTab('permissions')}
          className={`flex-1 px-4 py-3 font-semibold text-center border-b-2 ${
            activeTab === 'permissions'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent  hover:'
          }`} style={{color: "var(--foreground)"}}
        >
          <Shield className="w-4 h-4 inline mr-2" />
          Permissions
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`flex-1 px-4 py-3 font-semibold text-center border-b-2 ${
            activeTab === 'audit'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent  hover:'
          }`} style={{color: "var(--foreground)"}}
        >
          <Clock className="w-4 h-4 inline mr-2" />
          Audit Log
        </button>
      </div>

      {/* Permissions Tab */}
      {activeTab === 'permissions' && (
        <div className="space-y-6">
          {/* Grant New Permission */}
          <div className="bg-white dark:bg-slate-900 rounded-lg border dark:border-slate-700 p-6">
            <h3 className="text-lg font-semibold mb-4">Grant Permission</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium  mb-2" style={{color: "var(--foreground)"}}>
                  Permission
                </label>
                <select
                  value={newPermission}
                  onChange={(e) => setNewPermission(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                >
                  <option value="">Select a permission...</option>
                  {availablePermissions
                    .filter((p) => !permissions.some((up) => up.permission === p))
                    .map((permission) => (
                      <option key={permission} value={permission}>
                        {permission.replace(/_/g, ' ')}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium  mb-2" style={{color: "var(--foreground)"}}>
                  Reason (optional)
                </label>
                <input
                  type="text"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Why is this permission being granted?"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <button
                onClick={handleGrantPermission}
                disabled={!newPermission}
                className="w-full px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold flex items-center justify-center space-x-2"
              >
                <Plus className="w-4 h-4" />
                <span>Grant Permission</span>
              </button>
            </div>
          </div>

          {/* Current Permissions */}
          <div className="bg-white dark:bg-slate-900 rounded-lg border dark:border-slate-700 p-6">
            <h3 className="text-lg font-semibold mb-4">Current Permissions ({permissions.length})</h3>
            {permissions.length === 0 ? (
              <p className=" text-center py-8" style={{color: "var(--muted-foreground)"}}>No permissions granted</p>
            ) : (
              <div className="space-y-2">
                {permissions.map((permission) => (
                  <div
                    key={permission.permission}
                    className="flex items-center justify-between p-3 rounded-lg" style={{backgroundColor: "var(--background)"}}
                  >
                    <div className="flex items-center space-x-3">
                      <Shield className="w-5 h-5 text-sky-600" />
                      <span className="font-medium " style={{color: "var(--foreground)"}}>
                        {permission.permission.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <button
                      onClick={() => handleRevokePermission(permission.permission)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Revoke permission"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Audit Log Tab */}
      {activeTab === 'audit' && (
        <div className="bg-white dark:bg-slate-900 rounded-lg border dark:border-slate-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b" style={{backgroundColor: "var(--background)"}}>
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold " style={{color: "var(--foreground)"}}>Action</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold " style={{color: "var(--foreground)"}}>Permission</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold " style={{color: "var(--foreground)"}}>Admin</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold " style={{color: "var(--foreground)"}}>Reason</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold " style={{color: "var(--foreground)"}}>Date</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {auditLogs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center " style={{color: "var(--muted-foreground)"}}>
                      No audit logs
                    </td>
                  </tr>
                ) : (
                  auditLogs.map((log, index) => (
                    <tr key={index} className="hover:" style={{backgroundColor: "var(--background)"}}>
                      <td className="px-6 py-3 text-sm">
                        <span
                          className={`px-2 py-1 rounded text-xs font-semibold ${
                            log.action === 'grant'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {log.action}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-sm " style={{color: "var(--foreground)"}}>{log.permission.replace(/_/g, ' ')}</td>
                      <td className="px-6 py-3 text-sm " style={{color: "var(--muted-foreground)"}}>{log.admin_id}</td>
                      <td className="px-6 py-3 text-sm " style={{color: "var(--muted-foreground)"}}>{log.reason || '-'}</td>
                      <td className="px-6 py-3 text-sm " style={{color: "var(--muted-foreground)"}}>
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserPermissionsPanel;
