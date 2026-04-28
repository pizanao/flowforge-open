import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, useApi } from "../hooks/useApi";
import { NODE_TYPES, WORKFLOW_STATUS } from "../utils/formatters";
import { Badge } from "../components/ui/Badge";
import { MetricBox } from "../components/ui/MetricBox";
import { LoadingState } from "../components/ui/LoadingState";
import { ErrorState } from "../components/ui/ErrorState";
import { NodeDetailDrawer } from "../components/NodeDetailDrawer";
import { CanvasEditor } from "../features/canvas/CanvasEditor";
import { NodePalette } from "../features/palette/NodePalette";
import { RunHistory } from "../features/runs/RunHistory";
import { DurationChart } from "../features/runs/DurationChart";

export function WorkflowEditorPage({
  workflowId, onBack,
  nodeStates = {}, onNodeClick = null,
  selectedNodeId = null, onCloseDrawer = null,
  runStatus = "idle", progress = { completed: 0, total: 0 },
  onRun,
}) {
  const { data: workflow, loading, error, refetch } = useApi(`workflows/${workflowId}`);
  const [tab, setTab] = useState("canvas");

  const prevRunStatusRef = useRef(runStatus);
  useEffect(() => {
    const prev = prevRunStatusRef.current;
    prevRunStatusRef.current = runStatus;
    if ((prev === "running" || prev === "pending") && (runStatus === "success" || runStatus === "failed")) {
      refetch();
    }
  }, [runStatus, refetch]);

  const [localNodes, setLocalNodes] = useState([]);
  const [localEdges, setLocalEdges] = useState([]);
  const [saveStatus, setSaveStatus] = useState("saved");
  const [validating, setValidating] = useState(false);
  const [nodeErrors, setNodeErrors] = useState({});
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);

  const localNodesRef = useRef([]);
  const localEdgesRef = useRef([]);
  const saveTimerRef = useRef(null);
  const doSaveRef = useRef(null);
  const undoStackRef = useRef([]);
  const redoStackRef = useRef([]);

  useEffect(() => { localNodesRef.current = localNodes; }, [localNodes]);
  useEffect(() => { localEdgesRef.current = localEdges; }, [localEdges]);

  const lastIdRef = useRef(null);
  useEffect(() => {
    if (workflow && workflow.id !== lastIdRef.current) {
      lastIdRef.current = workflow.id;
      setLocalNodes(workflow.nodes || []);
      setLocalEdges((workflow.edges || []).map(e => ({ ...e, source: String(e.source_node), target: String(e.target_node) })));
      setSaveStatus("saved");
    }
  }, [workflow]);

  const doSave = useCallback(async () => {
    const nodes = localNodesRef.current;
    const edges = localEdgesRef.current;
    setSaveStatus("saving");
    try {
      const res = await apiFetch(`/api/workflows/${workflowId}/save_graph/`, {
        method: "PUT",
        body: JSON.stringify({
          nodes: nodes.map(n => ({ id: n.id, node_type: n.node_type, label: n.label, config: n.config || {}, position_x: Math.round(n.position_x), position_y: Math.round(n.position_y) })),
          edges: edges.map(e => ({ source_node: e.source, target_node: e.target, source_handle: e.source_handle || "default", label: e.label || "" })),
        }),
      });
      if (res.ok) {
        const fresh = await res.json();
        setLocalNodes(fresh.nodes || []);
        setLocalEdges((fresh.edges || []).map(e => ({ ...e, source: String(e.source_node), target: String(e.target_node) })));
        lastIdRef.current = fresh.id;
        setSaveStatus("saved");
      } else { setSaveStatus("unsaved"); }
    } catch { setSaveStatus("unsaved"); }
  }, [workflowId]);

  useEffect(() => { doSaveRef.current = doSave; }, [doSave]);

  const triggerAutoSave = useCallback(() => {
    setSaveStatus("unsaved");
    clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => doSaveRef.current?.(), 2000);
  }, []);

  const pushHistory = useCallback((nodes, edges) => {
    undoStackRef.current = [...undoStackRef.current.slice(-19), { nodes: nodes.map(n => ({ ...n })), edges: edges.map(e => ({ ...e })) }];
    redoStackRef.current = [];
    setCanUndo(true);
    setCanRedo(false);
  }, []);

  const handleUndo = useCallback(() => {
    if (!undoStackRef.current.length) return;
    const snap = undoStackRef.current[undoStackRef.current.length - 1];
    redoStackRef.current = [...redoStackRef.current, { nodes: [...localNodesRef.current], edges: [...localEdgesRef.current] }];
    undoStackRef.current = undoStackRef.current.slice(0, -1);
    setLocalNodes(snap.nodes);
    setLocalEdges(snap.edges);
    setCanUndo(undoStackRef.current.length > 0);
    setCanRedo(true);
    triggerAutoSave();
  }, [triggerAutoSave]);

  const handleRedo = useCallback(() => {
    if (!redoStackRef.current.length) return;
    const snap = redoStackRef.current[redoStackRef.current.length - 1];
    undoStackRef.current = [...undoStackRef.current, { nodes: [...localNodesRef.current], edges: [...localEdgesRef.current] }];
    redoStackRef.current = redoStackRef.current.slice(0, -1);
    setLocalNodes(snap.nodes);
    setLocalEdges(snap.edges);
    setCanUndo(true);
    setCanRedo(redoStackRef.current.length > 0);
    triggerAutoSave();
  }, [triggerAutoSave]);

  const handleNodeMoved = useCallback((nodeId, x, y) => {
    pushHistory(localNodesRef.current, localEdgesRef.current);
    setLocalNodes(prev => prev.map(n => n.id === nodeId ? { ...n, position_x: x, position_y: y } : n));
    triggerAutoSave();
  }, [pushHistory, triggerAutoSave]);

  const handleNodeAdd = useCallback((nodeType, x, y) => {
    const nt = NODE_TYPES[nodeType];
    const newNode = { id: crypto.randomUUID(), node_type: nodeType, label: nt?.label || nodeType, config: {}, position_x: Math.max(10, x), position_y: Math.max(10, y) };
    pushHistory(localNodesRef.current, localEdgesRef.current);
    setLocalNodes(prev => [...prev, newNode]);
    triggerAutoSave();
  }, [pushHistory, triggerAutoSave]);

  const handleEdgeCreate = useCallback((sourceId, targetId) => {
    if (sourceId === targetId) return;
    if (localEdgesRef.current.some(e => e.source === sourceId && e.target === targetId)) return;
    pushHistory(localNodesRef.current, localEdgesRef.current);
    setLocalEdges(prev => [...prev, { id: crypto.randomUUID(), source: sourceId, target: targetId, source_handle: "default", label: "" }]);
    triggerAutoSave();
  }, [pushHistory, triggerAutoSave]);

  const handleClearCanvas = useCallback(() => {
    pushHistory(localNodesRef.current, localEdgesRef.current);
    setLocalNodes([]); setLocalEdges([]);
    triggerAutoSave();
  }, [pushHistory, triggerAutoSave]);

  const handleSaveNow = useCallback(() => {
    clearTimeout(saveTimerRef.current);
    doSaveRef.current?.();
  }, []);

  const handleConfigChange = useCallback((nodeId, newConfig) => {
    setLocalNodes(prev => prev.map(n => n.id === nodeId ? { ...n, config: newConfig } : n));
    triggerAutoSave();
  }, [triggerAutoSave]);

  const handleDeleteNode = useCallback((nodeId) => {
    if (!nodeId) return;
    pushHistory(localNodesRef.current, localEdgesRef.current);
    setLocalNodes(prev => prev.filter(n => n.id !== nodeId));
    setLocalEdges(prev => prev.filter(e => e.source !== nodeId && e.target !== nodeId));
    onCloseDrawer?.();
    triggerAutoSave();
  }, [pushHistory, onCloseDrawer, triggerAutoSave]);

  const handleValidate = useCallback(async () => {
    setValidating(true); setNodeErrors({});
    try {
      const res = await apiFetch(`/api/workflows/${workflowId}/validate/`, { method: "POST" });
      const data = await res.json();
      const errs = {};
      (data.errors || []).forEach(e => { if (e.node_id) errs[e.node_id] = e.message; });
      setNodeErrors(errs);
      if (data.valid) { setNodeErrors({ __valid: true }); setTimeout(() => setNodeErrors({}), 2500); }
    } catch {}
    finally { setValidating(false); }
  }, [workflowId]);

  const handleDeleteWorkflow = useCallback(async () => {
    if (!window.confirm(`Excluir "${workflow?.name}"?\n\nTodos os nós, conexões e histórico serão removidos.`)) return;
    try { await apiFetch(`/api/workflows/${workflowId}/`, { method: "DELETE" }); onBack?.(); } catch {}
  }, [workflowId, workflow?.name, onBack]);

  const handleSaveAs = useCallback(async () => {
    const nome = window.prompt("Nome para o novo fluxo:", `${workflow?.name} (cópia)`);
    if (!nome?.trim()) return;
    try {
      const dupRes = await apiFetch(`/api/workflows/${workflowId}/duplicate/`, { method: "POST" });
      if (!dupRes.ok) return;
      const dup = await dupRes.json();
      await apiFetch(`/api/workflows/${dup.id}/`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: nome.trim() }) });
      onBack?.();
    } catch {}
  }, [workflowId, workflow?.name, onBack]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
      if (e.key === "Delete" && selectedNodeId) handleDeleteNode(selectedNodeId);
      else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === "s") { e.preventDefault(); handleSaveNow(); }
      else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === "z") { e.preventDefault(); handleUndo(); }
      else if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.shiftKey && e.key === "z"))) { e.preventDefault(); handleRedo(); }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selectedNodeId, handleDeleteNode, handleSaveNow, handleUndo, handleRedo]);

  if (loading) return <LoadingState msg="Carregando workflow..." />;
  if (error) return <ErrorState msg={error} />;
  if (!workflow) return null;

  const runs = workflow.recent_runs || [];
  const isRunning = runStatus === "running" || runStatus === "pending";
  const showProgress = runStatus !== "idle" && progress.total > 0;
  const saveLabel = saveStatus === "saving" ? "Salvando..." : saveStatus === "saved" ? "✓ Salvo" : "Salvar";
  const saveColor = saveStatus === "saved" ? "var(--success)" : saveStatus === "saving" ? "var(--muted)" : "var(--accent)";

  return (
    <div className="fade-up">
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: showProgress ? 10 : 20 }}>
        <button onClick={onBack} style={{ padding: "6px 14px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--fg)", cursor: "pointer", fontSize: 12 }}>← Voltar</button>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <h2 style={{ fontSize: 17, fontWeight: 700 }}>{workflow.name}</h2>
            <Badge text={WORKFLOW_STATUS[workflow.status]?.label || workflow.status} color={WORKFLOW_STATUS[workflow.status]?.color || "#6b7280"} bg={WORKFLOW_STATUS[workflow.status]?.bg || "#6b728015"} />
          </div>
          <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 3 }}>{workflow.description}</p>
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <button onClick={handleSaveAs} style={{ padding: "7px 13px", background: "transparent", border: "1px solid var(--border)", borderRadius: 6, color: "var(--muted)", cursor: "pointer", fontSize: 11, fontFamily: "var(--mono)" }}>Salvar como</button>
          <button onClick={handleDeleteWorkflow} style={{ padding: "7px 13px", background: "transparent", border: "1px solid var(--danger)40", borderRadius: 6, color: "var(--danger)", cursor: "pointer", fontSize: 11, fontFamily: "var(--mono)" }}>Excluir</button>
          <button onClick={() => onRun?.(handleSaveNow)} disabled={isRunning} style={{ padding: "8px 20px", background: isRunning ? "var(--border)" : "var(--accent)", border: "none", borderRadius: 6, color: isRunning ? "var(--muted)" : "#fff", cursor: isRunning ? "default" : "pointer", fontSize: 12, fontWeight: 600, transition: "background 0.2s" }}>
            {isRunning ? "⏳ Executando..." : "▶ Executar"}
          </button>
        </div>
      </div>

      {showProgress && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ height: 3, background: "var(--border)", borderRadius: 2, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0}%`, background: runStatus === "failed" ? "var(--danger)" : "var(--accent)", transition: "width 0.3s ease", borderRadius: 2 }} />
          </div>
          <div style={{ fontSize: 10, color: "var(--muted)", fontFamily: "var(--mono)", marginTop: 4 }}>{progress.completed}/{progress.total} nós executados</div>
        </div>
      )}

      <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <MetricBox label="Nós" value={localNodes.length} unit="" color="var(--accent)" />
        <MetricBox label="Conexões" value={localEdges.length} unit="" color="var(--info)" />
        <MetricBox label="Execuções" value={runs.length} unit="" color="var(--success)" />
        <MetricBox label="Versão" value={workflow.version} unit="" color="var(--muted)" />
      </div>

      <nav style={{ display: "flex", gap: 0, borderBottom: "1px solid var(--border)", marginBottom: 12 }}>
        {[{ k: "canvas", l: "Editor" }, { k: "runs", l: "Execuções" }, { k: "chart", l: "Performance" }].map(t => (
          <button key={t.k} onClick={() => setTab(t.k)} style={{ padding: "8px 16px", background: "transparent", border: "none", borderBottom: tab === t.k ? "2px solid var(--accent)" : "2px solid transparent", color: tab === t.k ? "var(--fg)" : "var(--muted)", cursor: "pointer", fontSize: 12, fontFamily: "var(--font)", fontWeight: tab === t.k ? 600 : 400 }}>
            {t.l}{t.k === "runs" && runs.length > 0 && <span style={{ marginLeft: 5, padding: "1px 6px", borderRadius: 8, fontSize: 9, fontFamily: "var(--mono)", background: "var(--accent-dim)", color: "var(--accent)" }}>{runs.length}</span>}
          </button>
        ))}
      </nav>

      {tab === "canvas" && (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
            <button onClick={handleSaveNow} disabled={saveStatus === "saving" || saveStatus === "saved"} style={{ padding: "5px 14px", background: "transparent", border: `1px solid ${saveColor}`, borderRadius: 5, color: saveColor, cursor: saveStatus === "saved" ? "default" : "pointer", fontSize: 11, fontFamily: "var(--mono)", fontWeight: 500, transition: "all 0.2s" }}>{saveLabel}</button>
            <button onClick={handleValidate} disabled={validating} style={{ padding: "5px 14px", background: "transparent", border: "1px solid var(--border)", borderRadius: 5, color: validating ? "var(--muted)" : "var(--fg)", cursor: validating ? "default" : "pointer", fontSize: 11, fontFamily: "var(--mono)" }}>{validating ? "Validando..." : "✦ Validar"}</button>
            <button onClick={handleUndo} title="Ctrl+Z" disabled={!canUndo} style={{ padding: "5px 10px", background: "transparent", border: "1px solid var(--border)", borderRadius: 5, color: canUndo ? "var(--muted)" : "var(--border)", cursor: canUndo ? "pointer" : "default", fontSize: 13 }}>↩</button>
            <button onClick={handleRedo} title="Ctrl+Y" disabled={!canRedo} style={{ padding: "5px 10px", background: "transparent", border: "1px solid var(--border)", borderRadius: 5, color: canRedo ? "var(--muted)" : "var(--border)", cursor: canRedo ? "pointer" : "default", fontSize: 13 }}>↪</button>
            <button onClick={handleClearCanvas} style={{ padding: "5px 14px", background: "transparent", border: "1px solid var(--border)", borderRadius: 5, color: "var(--muted)", cursor: "pointer", fontSize: 11, fontFamily: "var(--mono)" }}>Limpar canvas</button>
            {nodeErrors.__valid && <span style={{ fontSize: 11, color: "var(--success)", fontFamily: "var(--mono)", fontWeight: 600 }}>✓ DAG válido</span>}
            {!nodeErrors.__valid && Object.keys(nodeErrors).length > 0 && <span style={{ fontSize: 11, color: "var(--danger)", fontFamily: "var(--mono)", fontWeight: 600 }}>{Object.keys(nodeErrors).length} erro(s)</span>}
            <span style={{ fontSize: 10, color: "var(--muted)", fontFamily: "var(--mono)", marginLeft: "auto" }}>{localNodes.length} nós · {localEdges.length} conexões</span>
          </div>
          <NodePalette />
          <CanvasEditor key={workflow.id} nodes={localNodes} edges={localEdges} nodeStates={nodeStates} nodeErrors={nodeErrors} onNodeClick={onNodeClick} onNodeMoved={handleNodeMoved} onNodeAdd={handleNodeAdd} onEdgeCreate={handleEdgeCreate} />
        </>
      )}
      {tab === "runs" && <RunHistory runs={runs} />}
      {tab === "chart" && <DurationChart runs={[]} />}

      <NodeDetailDrawer key={selectedNodeId} nodeId={selectedNodeId} nodeStates={nodeStates} nodes={localNodes} workflowId={workflowId} onClose={onCloseDrawer} onConfigChange={handleConfigChange} />
    </div>
  );
}
