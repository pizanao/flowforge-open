/**
 * Drawer lateral com configuração e detalhes de execução de um nó.
 * Aba "Configurar": formulário específico por tipo de nó + dry-run.
 * Aba "Execução": status, output e erro da última execução.
 */

import { useState } from "react";
import { apiFetch } from "../hooks/useApi";
import { RUN_STATUS, NODE_TYPES, formatDuration } from "../utils/formatters";
import { NodeConfigPanel } from "./NodeConfigPanels";

export function NodeDetailDrawer({ nodeId, nodeStates, nodes, workflowId, onClose, onConfigChange }) {
  // Todos os hooks antes de qualquer early return (regras dos hooks React)
  const node = nodes.find(n => n.id === nodeId);
  const exec = nodeStates?.[nodeId];
  // Tab padrão: "execucao" se o nó já foi executado, senão "config"
  // key={selectedNodeId} no pai garante remount ao trocar de nó
  const [tab, setTab] = useState(() => exec ? "execucao" : "config");
  const [dryRunResult, setDryRunResult] = useState(null);
  const [dryRunLoading, setDryRunLoading] = useState(false);

  if (!nodeId || !node) return null;

  const nt = NODE_TYPES[node.node_type] || NODE_TYPES.trigger;
  const ns = exec ? (RUN_STATUS[exec.status] || RUN_STATUS.pending) : null;

  const handleDryRun = async () => {
    setDryRunLoading(true);
    setDryRunResult(null);
    try {
      const res = await apiFetch(`/api/nodes/${nodeId}/dry-run/`, {
        method: "POST",
        body: JSON.stringify({ input_data: {} }),
        credentials: "include",
      });
      const data = await res.json();
      setDryRunResult(data);
    } catch (e) {
      setDryRunResult({ error: e.message, output_data: null, duration_ms: 0 });
    } finally {
      setDryRunLoading(false);
    }
  };

  const jsonBlock = (data) => (
    <pre style={{
      fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg)",
      background: "var(--bg)", borderRadius: 6, padding: "10px 12px",
      border: "1px solid var(--border)", overflow: "auto", maxHeight: 200,
      whiteSpace: "pre-wrap", wordBreak: "break-all", lineHeight: 1.6, margin: 0,
    }}>
      {data ? JSON.stringify(data, null, 2) : "{}"}
    </pre>
  );

  const sectionLabel = (text) => (
    <div style={{
      fontSize: 10, color: "var(--muted)", fontFamily: "var(--mono)",
      letterSpacing: 1.2, textTransform: "uppercase", marginBottom: 6,
    }}>{text}</div>
  );

  const tabStyle = (active) => ({
    flex: 1, padding: "8px 0", background: "transparent", border: "none",
    borderBottom: active ? "2px solid var(--accent)" : "2px solid transparent",
    color: active ? "var(--fg)" : "var(--muted)", cursor: "pointer",
    fontSize: 11, fontFamily: "var(--font)", fontWeight: active ? 600 : 400,
    transition: "color 0.15s",
  });

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", zIndex: 100 }}
      />
      {/* Drawer */}
      <div style={{
        position: "fixed", top: 0, right: 0, height: "100vh", width: 360,
        background: "var(--surface)", borderLeft: "1px solid var(--border)",
        zIndex: 101, display: "flex", flexDirection: "column",
        animation: "slideIn 0.2s ease-out",
      }}>
        <style>{`@keyframes slideIn { from { transform: translateX(100%) } to { transform: translateX(0) } }`}</style>

        {/* Header */}
        <div style={{ padding: "16px 18px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8, background: `${nt.color}20`,
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, flexShrink: 0,
          }}>{nt.icon}</div>
          <div style={{ flex: 1, overflow: "hidden" }}>
            <div style={{ fontSize: 13, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.label}</div>
            <div style={{ fontSize: 10, color: nt.color, fontFamily: "var(--mono)" }}>{nt.label}</div>
          </div>
          <button onClick={onClose} style={{
            background: "none", border: "none", color: "var(--muted)", cursor: "pointer",
            fontSize: 18, padding: "0 4px", lineHeight: 1,
          }}>✕</button>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", borderBottom: "1px solid var(--border)" }}>
          <button style={tabStyle(tab === "config")} onClick={() => setTab("config")}>Configurar</button>
          <button style={tabStyle(tab === "execucao")} onClick={() => setTab("execucao")}>
            Execução
            {exec && (
              <span style={{
                marginLeft: 5, padding: "1px 5px", borderRadius: 8, fontSize: 9,
                fontFamily: "var(--mono)", background: ns?.bg, color: ns?.color,
              }}>{ns?.label}</span>
            )}
          </button>
        </div>

        {/* Conteúdo */}
        <div style={{ flex: 1, overflow: "auto", padding: "16px 18px", display: "flex", flexDirection: "column", gap: 16 }}>

          {/* ── Aba Configurar ── */}
          {tab === "config" && (
            <>
              <NodeConfigPanel node={node} workflowId={workflowId} onChange={onConfigChange} />

              {/* Botão dry-run */}
              <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}>
                <button
                  onClick={handleDryRun}
                  disabled={dryRunLoading}
                  style={{
                    width: "100%", padding: "7px 0", background: dryRunLoading ? "var(--border)" : "var(--surface2)",
                    border: "1px solid var(--border)", borderRadius: 6, color: dryRunLoading ? "var(--muted)" : "var(--fg)",
                    cursor: dryRunLoading ? "default" : "pointer", fontSize: 12, fontWeight: 600,
                  }}
                >
                  {dryRunLoading ? "⏳ Testando..." : "▶ Testar nó"}
                </button>

                {dryRunResult && (
                  <div style={{ marginTop: 12 }}>
                    {dryRunResult.error ? (
                      <>
                        {sectionLabel("Erro")}
                        <div style={{
                          padding: "8px 12px", borderRadius: 6, background: "var(--danger)10",
                          border: "1px solid var(--danger)20", fontSize: 11, fontFamily: "var(--mono)",
                          color: "var(--danger)", whiteSpace: "pre-wrap",
                        }}>{dryRunResult.error}</div>
                      </>
                    ) : (
                      <>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                          {sectionLabel("Output")}
                          <span style={{ fontSize: 10, color: "var(--success)", fontFamily: "var(--mono)" }}>
                            ✓ {dryRunResult.duration_ms}ms
                          </span>
                        </div>
                        {jsonBlock(dryRunResult.output_data)}
                      </>
                    )}
                  </div>
                )}
              </div>
            </>
          )}

          {/* ── Aba Execução ── */}
          {tab === "execucao" && (
            <>
              {!exec ? (
                <div style={{ fontSize: 12, color: "var(--muted)", textAlign: "center", padding: "20px 0" }}>
                  Este nó ainda não foi executado.
                </div>
              ) : (
                <>
                  {/* Status + duração */}
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{
                      padding: "2px 10px", borderRadius: 4, fontSize: 10, fontWeight: 600,
                      fontFamily: "var(--mono)", color: ns.color, background: ns.bg,
                      border: `1px solid ${ns.color}25`, letterSpacing: 0.5,
                    }}>{ns.label}</span>
                    {exec.duration_ms > 0 && (
                      <span style={{ fontSize: 11, color: "var(--muted)", fontFamily: "var(--mono)" }}>
                        {formatDuration(exec.duration_ms)}
                      </span>
                    )}
                  </div>

                  {exec.status === "failed" && exec.error_message && (
                    <div>
                      {sectionLabel("Erro")}
                      <div style={{
                        padding: "10px 12px", borderRadius: 6, background: "var(--danger)10",
                        border: "1px solid var(--danger)20", fontSize: 11, fontFamily: "var(--mono)",
                        color: "var(--danger)", whiteSpace: "pre-wrap", wordBreak: "break-all",
                      }}>{exec.error_message}</div>
                    </div>
                  )}

                  <div>
                    {sectionLabel("Output")}
                    {jsonBlock(exec.output_data)}
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
