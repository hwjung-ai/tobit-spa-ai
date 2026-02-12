/**
 * Admin Dashboard - Main component
 * Manages user administration, system monitoring, and settings
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  Users, Settings, Activity, AlertCircle, TrendingUp,
  RefreshCw, Menu, X, Layers
} from 'lucide-react';
import ScreenAssetPanel from './ScreenAssetPanel';

interface DashboardTab {
  id: string;
  label: string;
  icon: React.ReactNode;
}

interface SystemHealth {
  status: string;
  resource?: {
    cpu_percent: number;
    memory_percent: number;
  };
}

interface Metrics {
  resources: Array<{
    cpu_percent: number;
    memory_percent: number;
  }>;
  api: Array<{
    endpoint: string;
    avg_latency: number;
    request_count: number;
  }>;
}

interface Alert {
  id: string;
  type: string;
  severity: string;
  message: string;
  timestamp: string;
}

interface User {
  user_id: string;
  username: string;
  email: string;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
  login_count: number;
}

const AdminDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const tabs: DashboardTab[] = [
    { id: 'overview', label: 'Overview', icon: <Activity className="w-5 h-5" /> },
    { id: 'screens', label: 'Screens', icon: <Layers className="w-5 h-5" /> },
    { id: 'users', label: 'Users', icon: <Users className="w-5 h-5" /> },
    { id: 'monitoring', label: 'Monitoring', icon: <TrendingUp className="w-5 h-5" /> },
    { id: 'alerts', label: 'Alerts', icon: <AlertCircle className="w-5 h-5" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-5 h-5" /> },
  ];

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [healthRes, metricsRes, alertsRes] = await Promise.all([
        fetch('/admin/system/health'),
        fetch('/admin/system/metrics'),
        fetch('/admin/system/alerts'),
      ]);

      if (healthRes.ok) {
        const data = await healthRes.json();
        setSystemHealth(data.health);
      }

      if (metricsRes.ok) {
        const data = await metricsRes.json();
        setMetrics(data.metrics);
      }

      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setAlerts(data.alerts || []);
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 bg-green-50';
      case 'warning':
        return 'text-yellow-600 bg-yellow-50';
      case 'critical':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-[var(--muted-foreground)] bg-[var(--surface-elevated)]';
    }
  };

  const renderOverview = () => (
    <div className="space-y-6">
      {/* System Health Status */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className={`p-6 rounded-lg border ${getHealthColor(systemHealth?.status || 'unknown')}`}>
          <div className="text-sm font-medium mb-2">System Status</div>
          <div className="text-2xl font-bold capitalize">{systemHealth?.status || 'Unknown'}</div>
        </div>

        <div className="p-6 rounded-lg border bg-sky-50 text-sky-600">
          <div className="text-sm font-medium mb-2">Active Alerts</div>
          <div className="text-2xl font-bold">{alerts.length}</div>
        </div>

        <div className="p-6 rounded-lg border bg-purple-50 text-purple-600">
          <div className="text-sm font-medium mb-2">Resources</div>
          <div className="text-sm space-y-1">
            <div>CPU: {systemHealth?.resource?.cpu_percent ? systemHealth.resource.cpu_percent.toFixed(1) : 'N/A'}%</div>
            <div>Mem: {systemHealth?.resource?.memory_percent ? systemHealth.resource.memory_percent.toFixed(1) : 'N/A'}%</div>
          </div>
        </div>

        <div className="p-6 rounded-lg border bg-indigo-50 text-indigo-600">
          <div className="text-sm font-medium mb-2">Last Updated</div>
          <div className="text-sm">{new Date().toLocaleTimeString()}</div>
        </div>
      </div>

      {/* Metrics Charts */}
      {metrics?.resources && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* CPU and Memory Chart */}
          <div className="bg-[var(--background)] p-6 rounded-lg border">
            <h3 className="text-lg font-semibold mb-4">Resource Usage</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={metrics.resources.slice(-24)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="cpu_percent" stroke="#ef4444" name="CPU %" />
                <Line type="monotone" dataKey="memory_percent" stroke="#f59e0b" name="Memory %" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* API Performance Chart */}
          {metrics?.api && (
            <div className="bg-[var(--background)] p-6 rounded-lg border">
              <h3 className="text-lg font-semibold mb-4">API Performance</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={metrics.api.slice(-12)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="avg_response_time_ms" fill="#3b82f6" name="Avg Response (ms)" />
                  <Bar dataKey="error_rate" fill="#ef4444" name="Error Rate" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderScreens = () => (
    <ScreenAssetPanel onScreenUpdate={() => {}} />
  );

  const renderUsers = () => (
    <UserManagementPanel />
  );

  const renderMonitoring = () => (
    <MonitoringPanel metrics={metrics} systemHealth={systemHealth} />
  );

  const renderAlerts = () => (
    <AlertsPanel alerts={alerts} />
  );

  const renderSettings = () => (
    <SettingsPanel />
  );

  return (
    <div className="flex h-screen " style={{ backgroundColor: "var(--surface-base)" }}>
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-20'}  text-white transition-all duration-300`} style={{ backgroundColor: "var(--surface-base)" }}>
        <div className="p-4 flex items-center justify-between">
          {sidebarOpen && <span className="font-bold text-lg">Admin</span>}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 hover: rounded" style={{ backgroundColor: "var(--surface-elevated)" }}
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        <nav className="mt-8 space-y-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-sky-600 text-white'
                  : ' hover:'
              }`} style={{ backgroundColor: "var(--surface-elevated)", color: "var(--foreground-secondary)" }}
            >
              {tab.icon}
              {sidebarOpen && <span>{tab.label}</span>}
            </button>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <header className="bg-[var(--background)] border-b  px-8 py-4 flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
          <h1 className="text-2xl font-bold " style={{ color: "var(--foreground)" }}>Admin Dashboard</h1>
          <button
            onClick={fetchDashboardData}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </header>

        <main className="p-8">
          {activeTab === 'overview' && renderOverview()}
          {activeTab === 'screens' && renderScreens()}
          {activeTab === 'users' && renderUsers()}
          {activeTab === 'monitoring' && renderMonitoring()}
          {activeTab === 'alerts' && renderAlerts()}
          {activeTab === 'settings' && renderSettings()}
        </main>
      </div>
    </div>
  );
};

export default AdminDashboard;


// Sub-components
const UserManagementPanel: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [, setLoading] = useState(false);
  const [page] = useState(1);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`/admin/users?page=${page}&per_page=20`);
      if (response.ok) {
        const data = await response.json() as { users: User[] };
        setUsers(data.users || []);
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">User Management</h2>
      </div>

      <div className="bg-[var(--background)] rounded-lg border overflow-hidden">
        <table className="w-full">
          <thead className=" border-b" style={{ backgroundColor: "var(--surface-base)" }}>
            <tr>
              <th className="px-6 py-3 text-left text-sm font-semibold " style={{ color: "var(--foreground)" }}>Username</th>
              <th className="px-6 py-3 text-left text-sm font-semibold " style={{ color: "var(--foreground)" }}>Email</th>
              <th className="px-6 py-3 text-left text-sm font-semibold " style={{ color: "var(--foreground)" }}>Status</th>
              <th className="px-6 py-3 text-left text-sm font-semibold " style={{ color: "var(--foreground)" }}>Last Login</th>
              <th className="px-6 py-3 text-left text-sm font-semibold " style={{ color: "var(--foreground)" }}>Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {users.map((user) => (
              <tr key={user.user_id} className="hover:" style={{ backgroundColor: "var(--surface-base)" }}>
                <td className="px-6 py-3 text-sm " style={{ color: "var(--foreground)" }}>{user.username}</td>
                <td className="px-6 py-3 text-sm " style={{ color: "var(--muted-foreground)" }}>{user.email}</td>
                <td className="px-6 py-3 text-sm">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${
                    user.is_active
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-6 py-3 text-sm " style={{ color: "var(--muted-foreground)" }}>
                  {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
                </td>
                <td className="px-6 py-3 text-sm">
                  <button className="text-sky-600 hover:underline">Manage</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const MonitoringPanel: React.FC<{ metrics: Metrics | null; systemHealth: SystemHealth | null }> = ({ systemHealth }) => (
  <div className="space-y-6">
    <h2 className="text-xl font-bold">System Monitoring</h2>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-[var(--background)] p-6 rounded-lg border">
        <h3 className="text-lg font-semibold mb-4">Resource Metrics</h3>
        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>CPU Usage</span>
              <span className="font-semibold">{systemHealth?.resource?.cpu_percent ? systemHealth.resource.cpu_percent.toFixed(1) : 'N/A'}%</span>
            </div>
            <div className="w-full  rounded-full h-2" style={{ backgroundColor: "var(--surface-elevated)" }}>
              <div
                className="bg-sky-600 h-2 rounded-full"
                style={{ width: `${Math.min(systemHealth?.resource?.cpu_percent || 0, 100)}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Memory Usage</span>
              <span className="font-semibold">{systemHealth?.resource?.memory_percent ? systemHealth.resource.memory_percent.toFixed(1) : 'N/A'}%</span>
            </div>
            <div className="w-full  rounded-full h-2" style={{ backgroundColor: "var(--surface-elevated)" }}>
              <div
                className="bg-yellow-600 h-2 rounded-full"
                style={{ width: `${Math.min(systemHealth?.resource?.memory_percent || 0, 100)}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
);

const AlertsPanel: React.FC<{ alerts: Alert[] }> = ({ alerts }) => (
  <div className="space-y-6">
    <h2 className="text-xl font-bold">System Alerts</h2>
    <div className="space-y-3">
      {alerts.length === 0 ? (
        <div className="bg-green-50 border border-green-200 text-green-800 p-4 rounded-lg">
          No active alerts
        </div>
      ) : (
        alerts.map((alert, index) => (
          <div
            key={index}
            className={`p-4 rounded-lg border ${
              alert.severity === 'critical'
                ? 'bg-red-50 border-red-200 text-red-800'
                : 'bg-yellow-50 border-yellow-200 text-yellow-800'
            }`}
          >
            <div className="font-semibold">{alert.message}</div>
            <div className="text-sm mt-1">{new Date(alert.timestamp).toLocaleString()}</div>
          </div>
        ))
      )}
    </div>
  </div>
);

const SettingsPanel: React.FC = () => (
  <div className="space-y-6">
    <h2 className="text-xl font-bold">System Settings</h2>
    <div className="bg-[var(--background)] p-6 rounded-lg border">
      <p className="" style={{ color: "var(--muted-foreground)" }}>Settings management interface coming soon...</p>
    </div>
  </div>
);
