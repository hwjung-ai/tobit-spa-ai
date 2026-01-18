"use client";

import ScreenAssetEditor from "@/components/admin/ScreenAssetEditor";
import { useParams } from "next/navigation";

export default function ScreenEditorPage() {
  const params = useParams();
  const screenId = params.screenId as string;

  return (
    <div className="space-y-4">
      <ScreenAssetEditor assetId={screenId} />
    </div>
  );
}
