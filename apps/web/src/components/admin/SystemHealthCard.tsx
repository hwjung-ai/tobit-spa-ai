/**
 * System Health Card Component
 * Displays real-time system health status with visual indicators
 */

import React from 'react';
import { AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';

interface SystemHealthData {
  status: 'healthy' | 'warning' | 'critical';
  resource?: {
    cpu_percent: number;
    memory_percent: number;
    memory_available_gb: number;
    disk_percent: number;
    disk_available_gb: number;
    timestamp: string;
  };
  api?: {
    total_requests: number;
    total_errors: number;
    error_rate: number;
    avg_response_time_ms: number;
    p95_response_time_ms: number;
    p99_response_time_ms: number;
    timestamp: string;
  };
  database?: {
    connection_count: number;
    pool_size: number;
    query_time_ms_avg: number;
    slow_queries: number;
    error_count: number;
    timestamp: string;
  };
  recent_alerts_count: number;
}

interface SystemHealthCardProps {
  data?: SystemHealthData;
  loading?: boolean;
}

const SystemHealthCard: React.FC<SystemHealthCardProps> = ({ data, loading = false }) => {
  if (loading) {
    return (
      <div className="bg-white rounded-lg border p-6 animate-pulse">
        <div className="h-6 bg-slate-200 rounded w-1/3 mb-4"></div>
        <div className="space-y-3">
          <div className="h-4 bg-slate-200 rounded"></div>
          <div className="h-4 bg-slate-200 rounded"></div>
          <div className="h-4 bg-slate-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-lg border p-6">
        <p className="text-slate-500">No health data available</p>
      </div>
    );
  }

  const getStatusIcon = () => {
    switch (data.status) {
      case 'healthy':
        return <CheckCircle className="w-6 h-6 text-green-600" />;
      case 'warning':
        return <AlertTriangle className="w-6 h-6 text-yellow-600" />;
      case 'critical':
        return <AlertCircle className="w-6 h-6 text-red-600" />;
    }
  };

  const getStatusColor = () => {
    switch (data.status) {
      case 'healthy':
        return 'bg-green-50 border-green-200 text-green-900';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200 text-yellow-900';
      case 'critical':
        return 'bg-red-50 border-red-200 text-red-900';
    }
  };

  const getProgressBarColor = (value: number) => {
    if (value >= 90) return 'bg-red-600';
    if (value >= 75) return 'bg-yellow-600';
    return 'bg-green-600';
  };

  return (
    <div className={`rounded-lg border p-6 ${getStatusColor()}`}>
      <div className="flex items-center space-x-3 mb-6">
        {getStatusIcon()}
        <div>
          <h3 className="text-lg font-semibold">System Status</h3>
          <p className="text-sm capitalize opacity-75">{data.status}</p>
        </div>
      </div>

      {/* Resource Metrics */}
      {data.resource && (
        <div className="space-y-4 border-t border-current border-opacity-20 pt-4">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span>CPU Usage</span>
              <span className="font-semibold">{data.resource.cpu_percent.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-slate-300 rounded-full h-2 opacity-30">
              <div
                className={`h-2 rounded-full ${getProgressBarColor(data.resource.cpu_percent)} transition-all`}
                style={{ width: `${Math.min(data.resource.cpu_percent, 100)}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-sm mb-2">
              <span>Memory Usage</span>
              <span className="font-semibold">{data.resource.memory_percent.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-slate-300 rounded-full h-2 opacity-30">
              <div
                className={`h-2 rounded-full ${getProgressBarColor(data.resource.memory_percent)} transition-all`}
                style={{ width: `${Math.min(data.resource.memory_percent, 100)}%` }}
              />
            </div>
            <p className="text-xs opacity-75 mt-1">
              Available: {data.resource.memory_available_gb.toFixed(1)} GB
            </p>
          </div>

          <div>
            <div className="flex justify-between text-sm mb-2">
              <span>Disk Usage</span>
              <span className="font-semibold">{data.resource.disk_percent.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-slate-300 rounded-full h-2 opacity-30">
              <div
                className={`h-2 rounded-full ${getProgressBarColor(data.resource.disk_percent)} transition-all`}
                style={{ width: `${Math.min(data.resource.disk_percent, 100)}%` }}
              />
            </div>
            <p className="text-xs opacity-75 mt-1">
              Available: {data.resource.disk_available_gb.toFixed(1)} GB
            </p>
          </div>
        </div>
      )}

      {/* API Metrics */}
      {data.api && (
        <div className="space-y-2 border-t border-current border-opacity-20 pt-4 mt-4">
          <div className="flex justify-between text-sm">
            <span>API Requests</span>
            <span className="font-semibold">{data.api.total_requests}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span>Error Rate</span>
            <span className="font-semibold">{(data.api.error_rate * 100).toFixed(2)}%</span>
          </div>
          <div className="flex justify-between text-sm">
            <span>Avg Response</span>
            <span className="font-semibold">{data.api.avg_response_time_ms.toFixed(0)}ms</span>
          </div>
        </div>
      )}

      {/* Recent Alerts */}
      {data.recent_alerts_count > 0 && (
        <div className="flex items-center space-x-2 border-t border-current border-opacity-20 pt-4 mt-4">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">
            {data.recent_alerts_count} active alert{data.recent_alerts_count !== 1 ? 's' : ''}
          </span>
        </div>
      )}
    </div>
  );
};

export default SystemHealthCard;
