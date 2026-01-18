/**
 * User Permissions Management Panel
 * Manage user permissions and view audit logs
 */

import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Shield, Clock } from 'lucide-react';

interface UserPermission {
  permission: string;
  granted_at?: string;
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
  const [user, setUser] = useState<any>(null);
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

  useEffect(() => {
    if (userId) {
      fetchUserDetails();
    }
  }, [userId]);

  const fetchUserDetails = async () => {
    if (!userId) return;

    setLoading(true);
    try {
      const [userRes, auditRes] = await Promise.all([
        fetch(`/api/admin/users/${userId}`),
        fetch(`/api/admin/users/${userId}/audit-log`),
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
  };

  const handleGrantPermission = async () => {
    if (!newPermission || !userId) return;

    try {
      const response = await fetch(`/api/admin/users/${userId}/permissions/grant`, {
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
      const response = await fetch(`/api/admin/users/${userId}/permissions/revoke`, {
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
      <div className="bg-white rounded-lg border p-8 text-center">
        <p className="text-gray-500">Select a user to manage permissions</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg border p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center">
        <p className="text-gray-500">User not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* User Header */}
      <div className="bg-white rounded-lg border p-6">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
            <span className="text-xl font-semibold text-blue-600">
              {user.username.charAt(0).toUpperCase()}
            </span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">{user.username}</h2>
            <p className="text-gray-600">{user.email}</p>
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
            <p className="text-gray-500">Login Count</p>
            <p className="text-lg font-semibold">{user.login_count}</p>
          </div>
          <div>
            <p className="text-gray-500">Last Login</p>
            <p className="text-sm font-semibold">
              {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
            </p>
          </div>
          <div>
            <p className="text-gray-500">Created</p>
            <p className="text-sm font-semibold">
              {new Date(user.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b bg-white rounded-t-lg">
        <button
          onClick={() => setActiveTab('permissions')}
          className={`flex-1 px-4 py-3 font-semibold text-center border-b-2 ${
            activeTab === 'permissions'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          <Shield className="w-4 h-4 inline mr-2" />
          Permissions
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`flex-1 px-4 py-3 font-semibold text-center border-b-2 ${
            activeTab === 'audit'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          <Clock className="w-4 h-4 inline mr-2" />
          Audit Log
        </button>
      </div>

      {/* Permissions Tab */}
      {activeTab === 'permissions' && (
        <div className="space-y-6">
          {/* Grant New Permission */}
          <div className="bg-white rounded-lg border p-6">
            <h3 className="text-lg font-semibold mb-4">Grant Permission</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-900 mb-2">
                  Permission
                </label>
                <select
                  value={newPermission}
                  onChange={(e) => setNewPermission(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                <label className="block text-sm font-medium text-gray-900 mb-2">
                  Reason (optional)
                </label>
                <input
                  type="text"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Why is this permission being granted?"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <button
                onClick={handleGrantPermission}
                disabled={!newPermission}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold flex items-center justify-center space-x-2"
              >
                <Plus className="w-4 h-4" />
                <span>Grant Permission</span>
              </button>
            </div>
          </div>

          {/* Current Permissions */}
          <div className="bg-white rounded-lg border p-6">
            <h3 className="text-lg font-semibold mb-4">Current Permissions ({permissions.length})</h3>
            {permissions.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No permissions granted</p>
            ) : (
              <div className="space-y-2">
                {permissions.map((permission) => (
                  <div
                    key={permission.permission}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center space-x-3">
                      <Shield className="w-5 h-5 text-blue-600" />
                      <span className="font-medium text-gray-900">
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
        <div className="bg-white rounded-lg border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Action</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Permission</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Admin</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Reason</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {auditLogs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      No audit logs
                    </td>
                  </tr>
                ) : (
                  auditLogs.map((log, index) => (
                    <tr key={index} className="hover:bg-gray-50">
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
                      <td className="px-6 py-3 text-sm text-gray-900">{log.permission.replace(/_/g, ' ')}</td>
                      <td className="px-6 py-3 text-sm text-gray-600">{log.admin_id}</td>
                      <td className="px-6 py-3 text-sm text-gray-600">{log.reason || '-'}</td>
                      <td className="px-6 py-3 text-sm text-gray-600">
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
