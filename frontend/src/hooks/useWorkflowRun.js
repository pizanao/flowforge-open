/**
 * Hook para gerenciar execução de workflow com WebSocket.
 *
 * Abre WebSocket ao disparar execução e atualiza o estado
 * dos nós em tempo real conforme os eventos chegam.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { postAction } from "./useApi";

/**
 * @param {string} workflowId - UUID do workflow a executar
 * @param {function} onRunFinished - Callback chamado ao concluir/falhar (opcional)
 */
export function useWorkflowRun(workflowId, onRunFinished = null) {
  const [runId, setRunId] = useState(null);
  const [runStatus, setRunStatus] = useState("idle"); // idle | pending | running | success | failed
  const [nodeStates, setNodeStates] = useState({});   // { [nodeId]: { status, output_data, error_message, duration_ms } }
  const [progress, setProgress] = useState({ completed: 0, total: 0 });
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const wsRef = useRef(null);

  // Fecha o WebSocket atual se existir
  const closeWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onmessage = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Cleanup ao desmontar ou trocar de workflow
  useEffect(() => {
    return () => closeWs();
  }, [workflowId, closeWs]);

  const handleEvent = useCallback((event) => {
    switch (event.type) {
      case "run_snapshot":
        // Estado atual da run ao conectar tarde
        if (event.run_status === "running") setRunStatus("running");
        if (event.nodes_total) setProgress(p => ({ ...p, total: event.nodes_total, completed: event.nodes_completed || 0 }));
        if (event.node_executions) {
          const states = {};
          event.node_executions.forEach(ne => {
            states[ne.node_id] = {
              status: ne.status,
              output_data: ne.output_data,
              error_message: ne.error_message,
              duration_ms: ne.duration_ms,
            };
          });
          setNodeStates(states);
        }
        break;

      case "node_started":
        setNodeStates(prev => ({
          ...prev,
          [event.node_id]: { status: "running" },
        }));
        setProgress(p => ({ ...p, total: Math.max(p.total, event.execution_order + 1) }));
        break;

      case "node_completed":
        setNodeStates(prev => ({
          ...prev,
          [event.node_id]: {
            status: "success",
            output_data: event.output_data,
            duration_ms: event.duration_ms,
          },
        }));
        setProgress(p => ({ ...p, completed: p.completed + 1 }));
        break;

      case "node_failed":
        setNodeStates(prev => ({
          ...prev,
          [event.node_id]: {
            status: "failed",
            error_message: event.error_message,
            duration_ms: event.duration_ms,
          },
        }));
        setProgress(p => ({ ...p, completed: p.completed + 1 }));
        break;

      case "run_completed":
        setRunStatus("success");
        setProgress({ completed: event.nodes_completed, total: event.nodes_total });
        closeWs();
        if (onRunFinished) onRunFinished("success");
        break;

      case "run_failed":
        setRunStatus("failed");
        setProgress(p => ({ ...p, completed: event.nodes_completed }));
        closeWs();
        if (onRunFinished) onRunFinished("failed");
        break;

      default:
        break;
    }
  }, [closeWs, onRunFinished]);

  const openWebSocket = useCallback((id) => {
    closeWs();
    const token = localStorage.getItem("flowforge_token");
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const subprotocols = token ? ["flowforge.jwt", `jwt.${token}`] : ["flowforge.jwt"];
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/runs/${id}/`, subprotocols);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        handleEvent(JSON.parse(e.data));
      } catch {}
    };

    ws.onerror = () => {
      console.warn("[FlowForge] WebSocket error para run:", id);
    };

    ws.onclose = () => {
      wsRef.current = null;
    };
  }, [closeWs, handleEvent]);

  const startRun = useCallback(async () => {
    if (!workflowId) return;

    setRunStatus("pending");
    setNodeStates({});
    setProgress({ completed: 0, total: 0 });
    setSelectedNodeId(null);

    try {
      const result = await postAction(`workflows/${workflowId}/execute/`, {});
      if (result?.run_id) {
        setRunId(result.run_id);
        setRunStatus("running");
        openWebSocket(result.run_id);
      } else {
        setRunStatus("idle");
      }
    } catch {
      setRunStatus("idle");
    }
  }, [workflowId, openWebSocket]);

  const reset = useCallback(() => {
    closeWs();
    setRunId(null);
    setRunStatus("idle");
    setNodeStates({});
    setProgress({ completed: 0, total: 0 });
    setSelectedNodeId(null);
  }, [closeWs]);

  return {
    startRun,
    reset,
    runId,
    runStatus,
    nodeStates,
    progress,
    selectedNodeId,
    setSelectedNodeId,
    isRunning: runStatus === "running" || runStatus === "pending",
  };
}
