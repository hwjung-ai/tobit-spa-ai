import React, { useEffect, useRef, useState } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import Draggable, { DraggableData, DraggableEvent } from "react-draggable";
import CanvasComponent from "./CanvasComponent";
import { Component, ComponentType } from "@/lib/ui-screen/screen.schema";
import { PALETTE_DRAG_TYPE } from "./ComponentPalette";

interface LayoutProps {
    x: number;
    y: number;
    w: number;
    h: number;
}

const DEFAULT_ROW_HEIGHT = 60;
const COLS = 12;

export default function GridCanvas() {
    const containerRef = useRef<HTMLDivElement>(null);
    const [containerWidth, setContainerWidth] = useState(0);
    const editorState = useEditorState();
    const { screen, updateComponentProps, addComponent } = editorState;
    const [isDragOver, setIsDragOver] = useState(false);

    // Measure container width
    useEffect(() => {
        if (!containerRef.current) return;
        const observer = new ResizeObserver((entries) => {
            for (const entry of entries) {
                setContainerWidth(entry.contentRect.width);
            }
        });
        observer.observe(containerRef.current);
        return () => observer.disconnect();
    }, []);

    const colWidth = containerWidth / COLS;

    if (!screen) return null;

    // Render Grid Background
    const renderGridLines = () => {
        if (colWidth <= 0) return null;
        const lines = [];
        for (let i = 1; i < COLS; i++) {
            lines.push(
                <div
                    key={i}
                    className="absolute top-0 bottom-0 border-r /50"
                />
            );
        }
        // Render some horizontal lines for visual guide (every 4 rows?)
        const minHeight = 2000;
        for (let j = 1; j * DEFAULT_ROW_HEIGHT < minHeight; j++) {
            // Only show dotted lines every 3 rows to avoid clutter
            if (j % 3 === 0) {
                lines.push(
                    <div
                        key={`h-${j}`}
                        className="absolute left-0 right-0 border-b /30 border-dashed"
                    />
                );
            }
        }
        return lines;
    };

    const handleStop = (id: string, e: DraggableEvent, data: DraggableData) => {
        if (colWidth <= 0) return;
        const newX = Math.round(data.x / colWidth);
        const newY = Math.round(data.y / DEFAULT_ROW_HEIGHT);

        // Clamp
        const safeX = Math.max(0, Math.min(newX, COLS - 1));
        const safeY = Math.max(0, newY);

        const comp = screen.components.find((c) => c.id === id);
        if (!comp) return;

        const currentLayout = (comp.props?.layout as LayoutProps) || { x: 0, y: 0, w: 3, h: 2 };

        updateComponentProps(id, {
            ...comp.props,
            layout: { ...currentLayout, x: safeX, y: safeY }
        });
    };

    const handleDragOver = (e: React.DragEvent) => {
        if (e.dataTransfer.types.includes(PALETTE_DRAG_TYPE)) {
            e.preventDefault();
            e.dataTransfer.dropEffect = "copy";
            setIsDragOver(true);
        }
    };

    const handleDragLeave = (e: React.DragEvent) => {
        if (e.currentTarget === e.target) {
            setIsDragOver(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        const typeData = e.dataTransfer.getData(PALETTE_DRAG_TYPE);
        const componentType = typeData ? (typeData as ComponentType) : null;

        if (componentType && containerRef.current && colWidth > 0) {
            // 1. Add Component
            // addComponent is synchronous in state terms, but React render is async.
            // We rely on the store's static method to get the ID *after* calling the action.
            // Wait, standard zustand set is synchronous.
            addComponent(componentType);

            const newMessageId = useEditorState.getState().selectedComponentId;

            if (newMessageId) {
                const rect = containerRef.current.getBoundingClientRect();
                // Calculate scroll offset if any
                const scrollTop = containerRef.current.scrollTop || 0;

                const rawX = e.clientX - rect.left;
                const rawY = e.clientY - rect.top + scrollTop;

                const x = Math.min(Math.max(0, Math.floor(rawX / colWidth)), COLS - 1);
                const y = Math.max(0, Math.floor(rawY / DEFAULT_ROW_HEIGHT));

                // 3. Update Position
                updateComponentProps(newMessageId, {
                    layout: { x, y, w: 4, h: 2 } // Default 4x2 size
                });
            }
        }
    };

    return (
        <div className="flex flex-col h-full relative overflow-hidden">
            <div className="border-b p-3 flex justify-between items-center z-10">
                <h3 className="text-sm font-semibold">
                    Dashboard Canvas (Grid {COLS}x)
                </h3>
                <span className="text-xs 0">
                    Drag to move · Arrow keys to nudge · Snap enabled
                </span>
            </div>

            <div
                ref={containerRef}
                className={`flex-1 overflow-y-auto relative min-h-[500px] transition-colors ${isDragOver ? "bg-sky-950/20 ring-2 ring-inset ring-sky-500/30" : ""
                    }`}
                data-testid="grid-canvas"
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
            >
                {/* Helper Grid Layer */}
                <div className="absolute inset-0 pointer-events-none z-0">
                    {renderGridLines()}
                </div>

                {/* Components Layer */}
                <div className="relative z-10 min-h-[1000px]">
                    {screen.components.map((comp) => (
                        <GridItem
                            key={comp.id}
                            component={comp}
                            colWidth={colWidth}
                            rowHeight={DEFAULT_ROW_HEIGHT}
                            onStop={handleStop}
                            isSelected={editorState.selectedComponentIds.includes(comp.id)}
                            onSelect={() => editorState.selectComponent(comp.id)}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}

interface GridItemProps {
    component: Component;
    colWidth: number;
    rowHeight: number;
    onStop: (id: string, e: DraggableEvent, data: DraggableData) => void;
    isSelected: boolean;
    onSelect: () => void;
}

function GridItem({ component, colWidth, rowHeight, onStop, isSelected, onSelect }: GridItemProps) {
    // Default bounds if not set
    const layout = (component.props?.layout as LayoutProps) || { x: 0, y: 0, w: 4, h: 2 };

    // Calculate pixel position
    const x = layout.x * colWidth;
    const y = layout.y * rowHeight;
    const w = layout.w * colWidth;
    const h = layout.h * rowHeight;

    if (colWidth === 0) return null;

    return (
        <Draggable
            position={{ x, y }}
            grid={[colWidth, rowHeight]}
            onStop={(e, data) => onStop(component.id, e, data)}
            onMouseDown={(e) => {
                // Prevent event bubbling if clicking inside input etc (optional)
                onSelect();
            }}
            bounds="parent"
            handle=".drag-handle"
        >
            <div
                className={`absolute box-border transition-shadow ${isSelected ? "z-50 ring-2 ring-sky-500 shadow-lg shadow-sky-900/50" : "z-10 hover:z-20 border border-transparent hover:"
                    }`}
                onClick={(e) => {
                    e.stopPropagation();
                    onSelect();
                }}
            >
                {/* Drag Handle Overlay - only visible on hover or selected */}
                <div className="absolute top-0 right-0 left-0 h-4 cursor-move drag-handle group flex justify-center items-start opacity-0 hover:opacity-100 transition-opacity z-20">
                    <div className="w-8 h-1 /50 rounded-full mt-1"></div>
                </div>

                {/* Label for debugging/visual */}
                {isSelected && (
                    <div className="absolute -top-5 left-0 text-[10px] text-sky-300 font-mono px-1 rounded z-30">
                        x:{layout.x} y:{layout.y} w:{layout.w} h:{layout.h}
                    </div>
                )}

                <div className="w-full h-full overflow-hidden /20 rounded">
                    <CanvasComponent
                        component={component}
                        isSelected={isSelected}
                        onSelect={onSelect}
                        index={0}
                        parentId={null}
                        onReorder={() => { }}
                        isGridItem={true}
                    />
                </div>
            </div>
        </Draggable>
    );
}
