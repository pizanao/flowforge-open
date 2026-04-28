import { useState } from "react";
import { apiFetch } from "../../hooks/useApi";
import { NODE_TYPES, RUN_STATUS, formatDate, formatDuration } from "../../utils/formatters";
import { Badge } from "../../components/ui/Badge";

export function RunHistory({ runs }) {
  const [expanded, setExpanded] = useState(null);
  const [loadedExecutions, setLoadedExecutions] = useState({});

  const handleExpand = async (runId) => {
    if (expanded === runId) { setExpanded(null); return; }
    setExpanded(runId);
    if (!loadedExecutions[runId]) {
      try {
        const res = await apiFetch(`/api/runs/${runId}/`);
        const data = await res.json();
        setLoadedExecutions(prev => ({ ...prev, [runId]: data.node_executions || [] }));
      } catch {}
    }
  };

  if (!runs.length) {
    return (
      <div style={{ padding: 20, textAlign: "center", color: "var(--muted)", fontSize: 12 }}>
        Nenhuma execução ainda. Clique em "Executar" para rodar o workflow.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {runs.map(run => {
        const st = RUN_STATUS[run.status] || RUN_STATUS.pending;
        const nodeExecs = loadedExecutions[run.id] || [];
        return (
          <div key={run.id} style={{ background: "var(--surface)", borderRadius: 8, border: "1px solid var(--border)", overflow: "hidden" }}>
            <div
              onClick={() => handleExpand(run.id)}
              style={{ padding: "12px 16px", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Badge text={st.label} color={st.color} bg={st.bg} />
                <span style={{ fontSize: 11, color: "var(--muted)", fontFamily: "var(--mono)" }}>
                  {run.nodes_completed}/{run.nodes_total} nós · {formatDuration(run.duration_ms)}
                </span>
              </div>
              <span style={{ fontSize: 10, color: "var(--muted)", fontFamily: "var(--mono)" }}>
                {formatDate(run.created_at)}
              </span>
            </div>

            {expanded === run.id && (
              <div style={{ padding: "0 16px 14px", borderTop: "1px solid var(--border)" }}>
                {nodeExecs.length === 0 && (
                  <div style={{ padding: "10px 0", color: "var(--muted)", fontSize: 11 }}>Carregando...</div>
                )}
                <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 10 }}>
                  {nodeExecs.map((ne, i) => {
                    const nt = NODE_TYPES[ne.node_type] || NODE_TYPES.trigger;
                    const ns = RUN_STATUS[ne.status] || RUN_STATUS.pending;
                    return (
                      <div
                        key={i}
                        style={{
                          display: "flex", alignItems: "center", gap: 8, padding: "6px 10px",
                          borderRadius: 6, background: ne.status === "failed" ? "var(--danger)08" : "transparent",
                        }}
                      >
                        <span style={{ fontSize: 12 }}>{nt.icon}</span>
                        <span style={{ fontSize: 11, fontWeight: 500, flex: 1 }}>{ne.node_label}</span>
                        <span style={{ fontSize: 10, fontFamily: "var(--mono)", color: ns.color }}>{ns.label}</span>
                        <span style={{ fontSize: 10, fontFamily: "var(--mono)", color: "var(--muted)", width: 50, textAlign: "right" }}>
                          {formatDuration(ne.duration_ms)}
                        </span>
                      </div>
                    );
                  })}
                </div>
                {nodeExecs.some(n => n.error_message) && (
                  <div style={{ marginTop: 8, padding: "8px 10px", background: "var(--danger)10", borderRadius: 6, border: "1px solid var(--danger)20" }}>
                    <pre style={{ fontSize: 10, fontFamily: "var(--mono)", color: "var(--danger)", whiteSpace: "pre-wrap" }}>
                      {nodeExecs.find(n => n.error_message)?.error_message}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
