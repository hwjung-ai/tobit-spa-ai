"use client";

import { useEffect, useState } from "react";
import { OperationSetting, fetchApi } from "../../../lib/adminUtils";
import SettingsTable from "../../../components/admin/SettingsTable";
import SettingEditModal from "../../../components/admin/SettingEditModal";
import Toast from "../../../components/admin/Toast";

export default function SettingsPage() {
    const [settings, setSettings] = useState\u003cOperationSetting[]\u003e([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState\u003cstring | null\u003e(null);
    const [selectedSetting, setSelectedSetting] = useState\u003cOperationSetting | null\u003e(null);
    const [toast, setToast] = useState\u003c{ message: string; type: "success" | "error" | "warning"
} | null\u003e(null);

const loadSettings = async() =\u003e {
    setIsLoading(true);
setError(null);

try {
    const response = await fetchApi\u003c{ settings: OperationSetting[] }\u003e("/settings/operations");
    setSettings(response.data.settings);
} catch (err: any) {
    setError(err.message || "Failed to load settings");
} finally {
    setIsLoading(false);
}
  };

useEffect(() =\u003e {
    loadSettings();
}, []);

const handleEditSuccess = () =\u003e {
    loadSettings();

const setting = selectedSetting;
if (setting?.restart_required) {
    setToast({
        message: "✅ Setting updated successfully\n🔄 Restart required for this change to take effect",
        type: "warning",
    });
} else {
    setToast({
        message: "Setting updated successfully",
        type: "success",
    });
}
  };

return (
\u003cdiv className = "min-h-screen bg-slate-950 text-slate-100 p-6"\u003e
\u003cdiv className = "max-w-7xl mx-auto"\u003e
\u003cdiv className = "mb-6"\u003e
\u003ch1 className = "text-2xl font-semibold text-white mb-2"\u003eOperation Settings\u003c / h1\u003e
\u003cp className = "text-slate-400 text-sm"\u003e
            Manage system operation settings
\u003c / p\u003e
\u003c / div\u003e

{/* Warning Banner */ }
\u003cdiv className = "mb-6 p-4 bg-orange-950/30 border border-orange-800 rounded-lg"\u003e
\u003cdiv className = "flex items-center gap-2"\u003e
\u003csvg className = "h-5 w-5 text-orange-400" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24"\u003e
\u003cpath strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = { 2} d = "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /\u003e
\u003c / svg\u003e
\u003cp className = "text-orange-300 text-sm"\u003e
              Some settings require a system restart(shown with 🔄 icon)
\u003c / p\u003e
\u003c / div\u003e
\u003c / div\u003e

{/* Settings Table */ }
\u003cdiv className = "bg-slate-900 rounded-lg border border-slate-800 p-6"\u003e
{
    isLoading ? (
    \u003cdiv className = "text-center py-8 text-slate-400"\u003eLoading settings...\u003c / div\u003e
          ) : error ? (
    \u003cdiv className = "text-center py-8 text-red-400"\u003e{ error } \u003c / div\u003e
          ) : (
    \u003cSettingsTable settings = { settings } onEdit = { setSelectedSetting } /\u003e
          )
}
\u003c / div\u003e
\u003c / div\u003e

{/* Edit Modal */ }
{
    selectedSetting \u0026\u0026(
        \u003cSettingEditModal
          setting = { selectedSetting }
          onClose = {() =\u003e setSelectedSetting(null)}
onSuccess = { handleEditSuccess }
    /\u003e
      )}

{/* Toast */ }
{
    toast \u0026\u0026(
        \u003cToast
          message = { toast.message }
          type = { toast.type }
          onClose = {() =\u003e setToast(null)}
        /\u003e
      )}
\u003c / div\u003e
  );
}
