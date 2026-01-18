"use client";

import React, { useState, useEffect, useRef } from "react";

interface BuilderShellProps {
  leftPane?: React.ReactNode;
  centerTop?: React.ReactNode;
  centerBottom?: React.ReactNode;
  rightPane?: React.ReactNode;
  initialLeftWidth?: number;
  initialRightWidth?: number;
}

export default function BuilderShell({
  leftPane,
  centerTop,
  centerBottom,
  rightPane,
  initialLeftWidth = 280,
  initialRightWidth = 320,
}: BuilderShellProps) {
  const [leftWidth, setLeftWidth] = useState(initialLeftWidth);
  const [rightWidth, setRightWidth] = useState(initialRightWidth);
  const [isResizingLeft, setIsResizingLeft] = useState(false);
  const [isResizingRight, setIsResizingRight] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isResizingLeft && !isResizingRight) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();

      if (isResizingLeft) {
        setLeftWidth(Math.max(150, Math.min(rect.width / 2, e.clientX - rect.left)));
      } else if (isResizingRight) {
        const newRightWidth = rect.right - e.clientX;
        setRightWidth(Math.max(150, Math.min(rect.width / 2, newRightWidth)));
      }
    };

    const handleMouseUp = () => {
      setIsResizingLeft(false);
      setIsResizingRight(false);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizingLeft, isResizingRight]);

  return (
    <div
      ref={containerRef}
      className="flex h-full flex-col gap-4 overflow-hidden"
      style={{ userSelect: isResizingLeft || isResizingRight ? "none" : "auto" }}
    >
      <div className="flex h-full gap-0 overflow-hidden">
        {/* Left Pane */}
        <div
          className="flex-shrink-0 space-y-4 overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/70 p-4 shadow-inner shadow-black/40"
          style={{ width: `${leftWidth}px` }}
        >
          {leftPane}
        </div>

        {/* Left Resize Handle */}
        <div
          onMouseDown={(event) => {
            event.preventDefault();
            setIsResizingLeft(true);
          }}
          className={`group flex w-4 cursor-col-resize items-center justify-center transition-colors ${isResizingLeft ? "bg-sky-500/10" : "hover:bg-sky-500/5"
            }`}
        >
          <div className={`h-12 w-1 rounded-full bg-slate-800 transition-colors group-hover:bg-slate-700 ${isResizingLeft ? "bg-sky-500/50" : ""
            }`} />
        </div>

        {/* Center Pane */}
        <div className="flex flex-1 flex-col gap-4 overflow-hidden">
          <div className="flex-[3] overflow-auto rounded-3xl border border-slate-800 bg-slate-900/70 p-4 shadow-inner shadow-black/40 custom-scrollbar">
            {centerTop}
          </div>
          {centerBottom && (
            <div className="flex-shrink-0 overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/70 p-4 shadow-inner shadow-black/40">
              {centerBottom}
            </div>
          )}
        </div>

        {/* Right Resize Handle */}
        <div
          onMouseDown={(event) => {
            event.preventDefault();
            setIsResizingRight(true);
          }}
          className={`group flex w-4 cursor-col-resize items-center justify-center transition-colors ${isResizingRight ? "bg-sky-500/10" : "hover:bg-sky-500/5"
            }`}
        >
          <div className={`h-12 w-1 rounded-full bg-slate-800 transition-colors group-hover:bg-slate-700 ${isResizingRight ? "bg-sky-500/50" : ""
            }`} />
        </div>

        {/* Right Pane */}
        <div
          className="flex-shrink-0 overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-400 shadow-inner shadow-black/40"
          style={{ width: `${rightWidth}px` }}
        >
          {rightPane}
        </div>
      </div>
    </div>
  );
}
