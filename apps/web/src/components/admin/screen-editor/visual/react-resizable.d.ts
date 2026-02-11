declare module 'react-resizable' {
    import { CSSProperties, ReactNode } from 'react';

    export interface ResizeCallbackData {
        node: HTMLElement;
        size: { width: number; height: number };
        handle: string;
    }

    export interface ResizableProps {
        children: ReactNode;
        width: number;
        height: number;
        onResize?: (e: React.SyntheticEvent, data: ResizeCallbackData) => void;
        onResizeStart?: (e: React.SyntheticEvent, data: ResizeCallbackData) => void;
        onResizeStop?: (e: React.SyntheticEvent, data: ResizeCallbackData) => void;
        draggableOpts?: Record<string, unknown>;
        minConstraints?: [number, number];
        maxConstraints?: [number, number];
        lockAspectRatio?: boolean;
        axis?: 'both' | 'x' | 'y' | 'none';
        resizeHandles?: Array<'s' | 'w' | 'e' | 'n' | 'sw' | 'nw' | 'se' | 'ne'>;
        handle?: ReactNode | ((resizeHandle: string) => ReactNode);
        transformScale?: number;
        className?: string;
        style?: CSSProperties;
    }

    export class Resizable extends React.Component<ResizableProps> { }
}
