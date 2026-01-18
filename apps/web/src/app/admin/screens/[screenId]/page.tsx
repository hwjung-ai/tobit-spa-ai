"use client";

import ScreenEditor from "@/components/admin/screen-editor/ScreenEditor";
import { useParams } from "next/navigation";

export default function ScreenEditorPage() {
  const params = useParams();
  const screenId = params.screenId as string;

  return (
    <ScreenEditor assetId={screenId} />
  );
}
