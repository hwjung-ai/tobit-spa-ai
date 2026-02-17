/**
 * System Settings Panel Component
 * Manage system-wide configuration settings
 */

import React, { useState, useEffect } from 'react';
import { Save, RotateCcw, Eye, EyeOff } from 'lucide-react';
import { fetchApi } from '../../lib/adminUtils';
import { useConfirm } from '@/hooks/use-confirm';

interface Setting {
  key: string;
  value: unknown;
  category: string;
}

interface SystemSettingsPanelProps {
  onUpdate?: (settings: Record<string, unknown>) => void;
}

const SystemSettingsPanel: React.FC<SystemSettingsPanelProps> = ({ onUpdate }) => {
  const [categories, setCategories] = useState<Record<string, Setting[]>>({});
  const [selectedCategory, setSelectedCategory] = useState<string>('api');
  const [loading, setLoading] = useState(false);
  const [changes, setChanges] = useState<Record<string, unknown>>({});
  const [showPassword, setShowPassword] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
  const [confirmDialog, ConfirmDialogComponent] = useConfirm();

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      // fetchApi returns ResponseEnvelope, so access .data for the actual payload
      // Backend returns ResponseEnvelope.success(data={settings: {...}})
      const settingsData = await fetchApi<{ settings: Record<string, unknown> }>('/admin/settings');
      const categoriesData = await fetchApi<{ categories: Record<string, Setting[]> }>('/admin/settings/categories');

      setSettings(settingsData.data?.settings || {});
      setCategories(categoriesData.data?.categories || {});
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSettingChange = (key: string, value: unknown) => {
    setChanges({
      ...changes,
      [key]: value,
    });
  };

  const handleSaveChanges = async () => {
    if (Object.keys(changes).length === 0) {
      return;
    }

    setSaveStatus('saving');
    try {
      await fetchApi('/admin/settings', {
        method: 'PATCH',
        body: JSON.stringify({
          settings: changes,
          reason: 'Updated via admin dashboard',
        }),
      });

      setSaveStatus('success');
      setChanges({});
      await fetchSettings();
      onUpdate?.(changes);
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (error) {
      console.error('Failed to save settings:', error);
      setSaveStatus('error');
    }
  };

  const handleResetDefaults = async () => {
    const ok = await confirmDialog({
      title: "Reset Settings",
      description: "Are you sure you want to reset all settings to defaults?",
      confirmLabel: "Reset",
    });
    if (!ok) {
      return;
    }

    try {
      await fetchApi('/admin/settings/reset-defaults', {
        method: 'POST',
      });

      setChanges({});
      await fetchSettings();
    } catch (error) {
      console.error('Failed to reset settings:', error);
    }
  };

  const renderSettingInput = (key: string, value: unknown, currentValue?: unknown) => {
    const displayValue = currentValue !== undefined ? currentValue : value;

    if (typeof displayValue === 'boolean') {
      return (
        <select
          value={displayValue ? 'true' : 'false'}
          onChange={(e) => handleSettingChange(key, e.target.value === 'true')}
          className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
        >
          <option value="true">Enabled</option>
          <option value="false">Disabled</option>
        </select>
      );
    }

    if (typeof displayValue === 'number') {
      return (
        <input
          type="number"
          value={displayValue}
          onChange={(e) => handleSettingChange(key, parseInt(e.target.value))}
          className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
        />
      );
    }

    if (key.includes('password')) {
      return (
        <div className="relative">
          <input
            type={showPassword ? 'text' : 'password'}
            value={String(displayValue || '')}
            onChange={(e) => handleSettingChange(key, e.target.value as string)}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-2.5"

          >
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
      );
    }

    return (
      <input
        type="text"
        value={String(displayValue)}
        onChange={(e) => handleSettingChange(key, e.target.value)}
        className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
      />
    );
  };

  const categoryList = Object.keys(categories);
  const currentSettings = categories[selectedCategory] || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">System Settings</h2>
        <div className="flex space-x-2">
          {Object.keys(changes).length > 0 && (
            <button
              onClick={() => setChanges({})}
              className="px-4 py-2 rounded-lg hover:opacity-90"

            >
              Cancel
            </button>
          )}
          <button
            onClick={handleResetDefaults}
            className="px-4 py-2 flex items-center space-x-2 rounded-lg hover:opacity-90"

          >
            <RotateCcw className="w-4 h-4" />
            <span>Reset Defaults</span>
          </button>
          <button
            onClick={handleSaveChanges}
            disabled={Object.keys(changes).length === 0 || loading}
            className={`px-4 py-2 flex items-center space-x-2 rounded-lg font-semibold transition-colors ${
              saveStatus === 'saving'
                ? 'bg-sky-400 text-white cursor-wait'
                : saveStatus === 'success'
                ? 'bg-green-600 text-white'
                : saveStatus === 'error'
                ? 'bg-red-600 text-white'
                : 'bg-sky-600 text-white hover:bg-sky-700 dark:bg-sky-700 dark:hover:bg-sky-600 disabled:opacity-50 disabled:cursor-not-allowed'
            }`}
          >
            <Save className="w-4 h-4" />
            <span>{saveStatus === 'saving' ? 'Saving...' : saveStatus === 'success' ? 'Saved!' : 'Save Changes'}</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Category Sidebar */}
        <div className="lg:col-span-1">
          <nav className="space-y-1 bg-surface-base dark:bg-surface-base rounded-lg border dark:border-variant overflow-hidden">
            {categoryList.map((category) => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`w-full text-left px-4 py-3 text-sm font-medium transition-colors ${
                  selectedCategory === category
                    ? 'bg-sky-50 text-sky-700 border-l-4 border-sky-600'
                    : ''
                }`}
                style={selectedCategory === category ? {} : { color: "var(--foreground)" }}
              >
                <span className="capitalize">{category}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Settings Content */}
        <div className="lg:col-span-3">
          <div className="bg-surface-base dark:bg-surface-base rounded-lg border dark:border-variant p-6 space-y-6">
            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600 mx-auto"></div>
              </div>
            ) : currentSettings.length === 0 ? (
              <p className="text-center py-8">No settings in this category</p>
            ) : (
              currentSettings.map((setting) => {
                const settingKey = setting.key;
                const settingValue = setting.value;
                const currentValue = changes[settingKey] !== undefined ? changes[settingKey] : settingValue;
                const hasChanged = changes[settingKey] !== undefined;

                return (
                  <div key={settingKey} className="border-b pb-4 last:border-b-0">
                    <label className="block text-sm font-semibold mb-2">
                      {settingKey
                        .replace(/_/g, ' ')
                        .replace(/([A-Z])/g, ' $1')
                        .trim()
                        .charAt(0)
                        .toUpperCase() +
                        settingKey
                          .replace(/_/g, ' ')
                          .replace(/([A-Z])/g, ' $1')
                          .trim()
                          .slice(1)
                      }
                    </label>
                    <p className="text-xs mb-2">Setting: {settingKey}</p>
                    <div className={`mb-2 ${hasChanged ? 'p-3 bg-sky-50 rounded' : ''}`}>
                      {renderSettingInput(settingKey, settingValue, currentValue)}
                    </div>
                    {hasChanged && (
                      <p className="text-xs text-sky-600">
                        Changed from: {JSON.stringify(settingValue)}
                      </p>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Confirm Dialog */}
      <ConfirmDialogComponent />
    </div>
  );
};

export default SystemSettingsPanel;
