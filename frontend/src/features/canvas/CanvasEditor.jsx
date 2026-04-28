import { useCallback, useEffect, useRef, useState } from "react";
import { NODE_TYPES } from "../../utils/formatters";

const NODE_W = 160;
const NODE_H = 56;

export function CanvasEditor({
  nodes: initialNodes,
  edges,
  nodeStates = {},
  nodeErrors = {},
  onNodeClick = null,
  onNodeMoved = null,
  onNodeAdd = null,
  onEdgeCreate = null,
}) {
  const [nodes, setNodes] = useState(initialNodes);
  const [dragging, setDragging] = useState(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [drawingEdge, setDrawingEdge] = useState(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    setNodes(prev => {
      const prevMap = new Map(prev.map(n => [n.id, n]));
      const keepIds = new Set(initialNodes.map(n => n.id));
      const result = prev.filter(n => keepIds.has(n.id));
      initialNodes.forEach(n => { if (!prevMap.has(n.id)) result.push(n); });
      if (result.length === prev.length && result.every((n, i) => n.id === prev[i]?.id)) return prev;
      return result;
    });
  }, [initialNodes]);

  const handleNodeMouseDown = (e, nodeId) => {
    if (drawingEdge) return;
    e.stopPropagation();
    const node = nodes.find(n => n.id === nodeId);
    const rect = canvasRef.current.getBoundingClientRect();
    setDragging(nodeId);
    setOffset({ x: e.clientX - rect.left - node.position_x, y: e.clientY - rect.top - node.position_y });
  };

  const handleHandleMouseDown = (e, nodeId) => {
    e.stopPropagation();
    e.preventDefault();
    const rect = canvasRef.current.getBoundingClientRect();
    const node = nodes.find(n => n.id === nodeId);
    const x1 = node.position_x + NODE_W;
    const y1 = node.position_y + NODE_H / 2;
    setDrawingEdge({ sourceNodeId: nodeId, x1, y1, curX: x1, curY: y1 });
  };

  const handleMouseMove = useCallback((e) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    if (dragging) {
      setNodes(prev => prev.map(n =>
        n.id === dragging ? { ...n, position_x: Math.max(0, x - offset.x), position_y: Math.max(0, y - offset.y) } : n
      ));
    }
    if (drawingEdge) setDrawingEdge(prev => ({ ...prev, curX: x, curY: y }));
  }, [dragging, offset, drawingEdge]);

  const handleMouseUp = useCallback((e) => {
    if (dragging) {
      const movedNode = nodes.find(n => n.id === dragging);
      if (movedNode && onNodeMoved) onNodeMoved(movedNode.id, movedNode.position_x, movedNode.position_y);
      setDragging(null);
    }
    if (drawingEdge) {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (rect) {
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const target = nodes.find(n =>
          n.id !== drawingEdge.sourceNodeId &&
          x >= n.position_x && x <= n.position_x + NODE_W &&
          y >= n.position_y && y <= n.position_y + NODE_H
        );
        if (target && onEdgeCreate) onEdgeCreate(drawingEdge.sourceNodeId, target.id);
      }
      setDrawingEdge(null);
    }
  }, [dragging, drawingEdge, nodes, onNodeMoved, onEdgeCreate]);

  useEffect(() => {
    if (dragging || drawingEdge) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
      return () => {
        window.removeEventListener("mousemove", handleMouseMove);
        window.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [dragging, drawingEdge, handleMouseMove, handleMouseUp]);

  const handleDragOver = (e) => { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; };
  const handleDrop = (e) => {
    e.preventDefault();
    const nodeType = e.dataTransfer.getData("nodeType");
    if (!nodeType || !onNodeAdd) return;
    const rect = canvasRef.current.getBoundingClientRect();
    onNodeAdd(nodeType, e.clientX - rect.left - NODE_W / 2, e.clientY - rect.top - NODE_H / 2);
  };

  const getEdgePath = (edge) => {
    const src = nodes.find(n => n.id === edge.source);
    const tgt = nodes.find(n => n.id === edge.target);
    if (!src || !tgt) return "";
    const x1 = src.position_x + NODE_W, y1 = src.position_y + NODE_H / 2;
    const x2 = tgt.position_x, y2 = tgt.position_y + NODE_H / 2;
    const cx = (x1 + x2) / 2;
    return `M${x1},${y1} C${cx},${y1} ${cx},${y2} ${x2},${y2}`;
  };

  const getDrawingPath = () => {
    if (!drawingEdge) return "";
    const { x1, y1, curX, curY } = drawingEdge;
    const cx = (x1 + curX) / 2;
    return `M${x1},${y1} C${cx},${y1} ${cx},${curY} ${curX},${curY}`;
  };

  const getNodeStyle = (node) => {
    const nt = NODE_TYPES[node.node_type] || NODE_TYPES.trigger;
    const exec = nodeStates[node.id];
    const base = {
      position: "absolute", left: node.position_x, top: node.position_y,
      width: NODE_W, height: NODE_H, background: "var(--surface2)", borderRadius: 8,
      display: "flex", alignItems: "center", gap: 8, padding: "0 12px",
      cursor: dragging === node.id ? "grabbing" : "grab",
      transition: dragging === node.id ? "none" : "box-shadow 0.2s, border-color 0.2s",
      userSelect: "none", zIndex: dragging === node.id ? 10 : 1,
    };
    if (nodeErrors[node.id]) return { ...base, border: "1.5px solid var(--danger)", boxShadow: "0 0 10px #ef444440" };
    if (!exec) return { ...base, border: `1.5px solid ${nt.color}50`, boxShadow: dragging === node.id ? `0 4px 20px ${nt.color}30` : "none" };
    if (exec.status === "running") return { ...base, border: "1.5px solid #a855f7", animation: "pulse 1.5s ease-in-out infinite" };
    if (exec.status === "success") return { ...base, border: "1.5px solid var(--success)", boxShadow: "0 0 8px #10b98130" };
    if (exec.status === "failed") return { ...base, border: "1.5px solid var(--danger)", boxShadow: "0 0 8px #ef444430" };
    return { ...base, border: "1.5px dashed var(--border)", opacity: 0.6 };
  };

  const getExecIcon = (nodeId) => {
    const errMsg = nodeErrors[nodeId];
    const iconStyle = { position: "absolute", top: -6, right: -6, fontSize: 10, borderRadius: "50%", width: 16, height: 16, display: "flex", alignItems: "center", justifyContent: "center", zIndex: 2 };
    if (errMsg) return <span title={errMsg} style={{ ...iconStyle, background: "var(--danger)", cursor: "help" }}>!</span>;
    const exec = nodeStates[nodeId];
    if (!exec) return null;
    if (exec.status === "success") return <span style={{ ...iconStyle, background: "var(--success)" }}>✓</span>;
    if (exec.status === "failed") return <span style={{ ...iconStyle, background: "var(--danger)" }}>✕</span>;
    if (exec.status === "running") return <span style={{ ...iconStyle, width: 8, height: 8, top: -4, right: -4, background: "#a855f7" }} />;
    return null;
  };

  return (
    <div
      ref={canvasRef}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      style={{
        position: "relative", width: "100%", height: 420,
        background: "var(--surface)", borderRadius: 10,
        border: `1px solid ${drawingEdge ? "var(--accent)" : "var(--border)"}`,
        overflow: "hidden",
        backgroundImage: "radial-gradient(circle, #26263a 1px, transparent 1px)",
        backgroundSize: "24px 24px",
        cursor: drawingEdge ? "crosshair" : (dragging ? "grabbing" : "default"),
      }}
    >
      {nodes.length === 0 && (
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 8, pointerEvents: "none" }}>
          <div style={{ fontSize: 28 }}>⬇</div>
          <p style={{ fontSize: 12, color: "var(--muted)" }}>Arraste um tipo de nó do palete para cá</p>
        </div>
      )}

      <svg style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
        <defs>
          <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#a855f760" />
          </marker>
        </defs>
        {edges.map(e => {
          const srcRunning = nodeStates[e.source]?.status === "running";
          const pathD = getEdgePath(e);
          if (!pathD) return null;
          return (
            <g key={e.id}>
              <path id={`edge-path-${e.id}`} d={pathD} stroke={srcRunning ? "#a855f7" : "#a855f740"} strokeWidth={srcRunning ? 2.5 : 2} fill="none" markerEnd="url(#arrowhead)" />
              {srcRunning && (
                <circle r="4" fill="#a855f7" opacity="0.9">
                  <animateMotion dur="1.5s" repeatCount="indefinite">
                    <mpath href={`#edge-path-${e.id}`} />
                  </animateMotion>
                </circle>
              )}
              {e.label && (() => {
                const src = nodes.find(n => n.id === e.source);
                const tgt = nodes.find(n => n.id === e.target);
                if (!src || !tgt) return null;
                const mx = (src.position_x + NODE_W + tgt.position_x) / 2;
                const my = (src.position_y + tgt.position_y) / 2 + NODE_H / 2 - 6;
                return <text key="lbl" x={mx} y={my} fill="#a855f7" fontSize={9} fontFamily="var(--mono)" textAnchor="middle">{e.label}</text>;
              })()}
            </g>
          );
        })}
        {drawingEdge && <path d={getDrawingPath()} stroke="#a855f7" strokeWidth={2} strokeDasharray="6,4" fill="none" opacity={0.8} />}
      </svg>

      {nodes.map(node => {
        const nt = NODE_TYPES[node.node_type] || NODE_TYPES.trigger;
        return (
          <div key={node.id} onMouseDown={(e) => handleNodeMouseDown(e, node.id)} onClick={() => onNodeClick?.(node.id)} style={getNodeStyle(node)}>
            {getExecIcon(node.id)}
            <div style={{ position: "absolute", left: -5, top: "50%", transform: "translateY(-50%)", width: 10, height: 10, borderRadius: "50%", background: "var(--surface2)", border: `2px solid ${nt.color}80` }} />
            <div onMouseDown={(e) => handleHandleMouseDown(e, node.id)} style={{ position: "absolute", right: -5, top: "50%", transform: "translateY(-50%)", width: 10, height: 10, borderRadius: "50%", background: "var(--surface2)", border: `2px solid ${nt.color}80`, cursor: "crosshair", zIndex: 5 }} />
            <div style={{ width: 28, height: 28, borderRadius: 6, background: `${nt.color}20`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, flexShrink: 0 }}>{nt.icon}</div>
            <div style={{ overflow: "hidden" }}>
              <div style={{ fontSize: 11, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{node.label}</div>
              <div style={{ fontSize: 9, color: nt.color, fontFamily: "var(--mono)", letterSpacing: 0.5 }}>{nt.label}</div>
            </div>
          </div>
        );
      })}

      <div style={{ position: "absolute", bottom: 10, right: 14, fontSize: 10, color: "var(--muted)", fontFamily: "var(--mono)" }}>
        {drawingEdge ? "Solte sobre um nó para conectar" : "Arraste o handle direito (•) para conectar nós"}
      </div>
    </div>
  );
}
