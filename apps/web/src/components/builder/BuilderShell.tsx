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
      className="flex h-full flex-col gap-3 overflow-hidden"
      style={{userSelect: isResizingLeft || isResizingRight ? "none" : "auto"}}
    >
      <div className="flex h-full gap-0 overflow-hidden">
        {/* Left Pane */}
        <div
          className="flex-shrink-0 space-y-3 overflow-hidden rounded-2xl border p-3 shadow-md"
          style={{width: `${leftWidth}px`, backgroundColor: "var(--surface-elevated)", borderColor: "var(--border)"}}
        >
          {leftPane}
        </div>

        {/* Left Resize Handle */}
        <div
          onMouseDown={(event) => {
            event.preventDefault();
            setIsResizingLeft(true);
          }}
          className={`resize-handle-col ${isResizingLeft ? "is-active" : ""}`}
          aria-label="Resize left pane"
          role="separator"
          aria-orientation="vertical"
        >
          <div className="resize-handle-grip" />
        </div>

        {/* Center Pane */}
        <div className="flex flex-1 flex-col gap-3 overflow-hidden">
          <div className="flex-[3] overflow-auto rounded-2xl border p-3 shadow-sm custom-scrollbar"
            style={{backgroundColor: "var(--surface-base)", borderColor: "var(--border)"}}
          >
            {centerTop}
          </div>
          {centerBottom && (
            <div
              className="flex-shrink-0 overflow-hidden rounded-2xl border p-3 shadow-sm"
              style={{backgroundColor: "var(--surface-base)", borderColor: "var(--border)"}}
            >
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
          className={`resize-handle-col ${isResizingRight ? "is-active" : ""}`}
          aria-label="Resize right pane"
          role="separator"
          aria-orientation="vertical"
        >
          <div className="resize-handle-grip" />
        </div>

        {/* Right Pane */}
        <div
          className="flex-shrink-0 overflow-hidden rounded-2xl border p-3 text-sm shadow-md"
          style={{width: `${rightWidth}px`, backgroundColor: "var(--surface-elevated)", borderColor: "var(--border)", color: "var(--muted-foreground)"}}
        >
          {rightPane}
        </div>
      </div>
    </div>
  );
}
