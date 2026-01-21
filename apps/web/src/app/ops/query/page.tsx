"use client";

import React from 'react'

export default function OpsQueryPage() {
  const goToInspector = () => {
    // Navigate to inspector with a dummy trace id for testing purposes
    window.location.href = '/admin/inspector?trace_id=dummy-trace';
  };

  return (
    <div style={{ padding: '24px' }}>
      <button aria-label="Open Inspector" data-testid="ops-open-in-inspector" onClick={goToInspector} type="button">
        Open Inspector
      </button>
    </div>
  );
}
