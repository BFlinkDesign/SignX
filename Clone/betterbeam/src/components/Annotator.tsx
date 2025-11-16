import { useEffect, useRef, useState } from 'react';
import { Stage, Layer, Line, Rect, Text as KonvaText } from 'react-konva';
import type { KonvaEventObject } from 'konva/lib/Node';

type Tool = 'pen' | 'rect' | 'text' | 'select';

interface Point { x: number; y: number }
interface PenShape { type: 'pen'; points: number[]; stroke: string; strokeWidth: number }
interface RectShape { type: 'rect'; x: number; y: number; width: number; height: number; stroke: string; strokeWidth: number }
interface TextShape { type: 'text'; x: number; y: number; text: string; fill: string }
type Shape = PenShape | RectShape | TextShape;

export function Annotator() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState<{ w: number; h: number }>({ w: 0, h: 0 });
  const [tool, setTool] = useState<Tool>('pen');
  const [shapes, setShapes] = useState<Shape[]>([]);
  const [drawing, setDrawing] = useState<boolean>(false);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    setSize({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  const onPointerDown = (e: KonvaEventObject<PointerEvent>) => {
    const stage = e.target.getStage();
    if (!stage) return;
    const pos = stage.getPointerPosition() as Point | null;
    if (!pos) return;
    if (tool === 'pen') {
      setShapes(s => [...s, { type: 'pen', points: [pos.x, pos.y], stroke: '#e11d48', strokeWidth: 2 }]);
      setDrawing(true);
    } else if (tool === 'rect') {
      setShapes(s => [...s, { type: 'rect', x: pos.x, y: pos.y, width: 0, height: 0, stroke: '#0ea5e9', strokeWidth: 2 }]);
      setDrawing(true);
    } else if (tool === 'text') {
      const text = prompt('Text:') || '';
      if (text) setShapes(s => [...s, { type: 'text', x: pos.x, y: pos.y, text, fill: '#111827' }]);
    }
  };

  const onPointerMove = (e: KonvaEventObject<PointerEvent>) => {
    if (!drawing) return;
    const stage = e.target.getStage();
    if (!stage) return;
    const pos = stage.getPointerPosition() as Point | null;
    if (!pos) return;
    setShapes(s => {
      const copy = s.slice();
      const last = copy[copy.length - 1];
      if (!last) return copy;
      if (last.type === 'pen') {
        (last as PenShape).points = [...(last as PenShape).points, pos.x, pos.y];
      } else if (last.type === 'rect') {
        const r = last as RectShape;
        r.width = pos.x - r.x;
        r.height = pos.y - r.y;
      }
      return copy;
    });
  };

  const onPointerUp = () => setDrawing(false);

  const exportJSON = () => {
    const data = JSON.stringify(shapes);
    // eslint-disable-next-line no-alert
    alert(data);
  };
  const importJSON = () => {
    const data = prompt('Paste JSON:');
    if (data) setShapes(JSON.parse(data));
  };

  return (
    <div ref={containerRef} className="annotator">
      <div className="annotator-tools">
        <button onClick={() => setTool('pen')} className={tool === 'pen' ? 'active' : ''}>Pen</button>
        <button onClick={() => setTool('rect')} className={tool === 'rect' ? 'active' : ''}>Rect</button>
        <button onClick={() => setTool('text')} className={tool === 'text' ? 'active' : ''}>Text</button>
        <button onClick={exportJSON}>Export</button>
        <button onClick={importJSON}>Import</button>
      </div>
      <Stage width={size.w} height={size.h} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp}>
        <Layer>
          {shapes.map((s, i) => {
            if (s.type === 'pen') return <Line key={i} points={s.points} stroke={s.stroke} strokeWidth={s.strokeWidth} lineCap="round" lineJoin="round" />;
            if (s.type === 'rect') return <Rect key={i} x={s.x} y={s.y} width={s.width} height={s.height} stroke={s.stroke} strokeWidth={s.strokeWidth} />;
            if (s.type === 'text') return <KonvaText key={i} x={s.x} y={s.y} text={s.text} fill={s.fill} />;
            return null;
          })}
        </Layer>
      </Stage>
    </div>
  );
}


