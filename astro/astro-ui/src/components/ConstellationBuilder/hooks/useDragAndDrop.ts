'use client';

import { useCallback } from 'react';
import { useReactFlow, XYPosition } from 'reactflow';
import { PaletteItem } from '../types';

interface UseDragAndDropOptions {
  addNode: (item: PaletteItem, position: XYPosition) => void;
}

export interface UseDragAndDropReturn {
  onDragOver: (event: React.DragEvent) => void;
  onDrop: (event: React.DragEvent) => void;
}

export function useDragAndDrop({
  addNode,
}: UseDragAndDropOptions): UseDragAndDropReturn {
  const reactFlowInstance = useReactFlow();

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const data = event.dataTransfer.getData('application/reactflow');
      if (!data) return;

      try {
        const paletteItem: PaletteItem = JSON.parse(data);

        // Get the drop position relative to the React Flow canvas
        const position = reactFlowInstance.screenToFlowPosition({
          x: event.clientX,
          y: event.clientY,
        });

        // Offset to center the node on the drop point
        const adjustedPosition: XYPosition = {
          x: position.x - 140, // Half of star node width (280/2)
          y: position.y - 50, // Approximate half of star node height
        };

        addNode(paletteItem, adjustedPosition);
      } catch (error) {
        console.error('Failed to parse dropped item:', error);
      }
    },
    [reactFlowInstance, addNode]
  );

  return {
    onDragOver,
    onDrop,
  };
}
