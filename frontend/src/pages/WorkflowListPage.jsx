import { useState } from "react";
import { apiFetch, useApi } from "../hooks/useApi";
import { WORKFLOW_STATUS } from "../utils/formatters";
import { Badge } from "../components/ui/Badge";
import { MetricBox } from "../components/ui/MetricBox";
import { LoadingState } from "../components/ui/LoadingState";
import { ErrorState } from "../components/ui/ErrorState";

const CATEGORY_ICONS = { "IA": "🤖", "Monitoramento": "📡", "Dados": "🗄️" };

export function WorkflowListPage({ onSelect }) {
  const { data: workflows, loading, error } = useApi("workflows");
  const { data: stats } = useApi("workflows/stats");
  const { data: templates } = useApi("workflows/templates");
  const [creatingTemplate, setCreatingTemplate] = useState(null);

  const handleUseTemplate = async (slug) => {
    setCreatingTemplate(slug);
    try {
      const res = await apiFetch(`/api/workflows/from-template/${slug}/`, { method: "POST" });
      if (res.ok) {
        const wf = await res.json();
        onSelect(wf);
      }
    } catch {}
    finally { setCreatingTemplate(null); }
  };

  if (loading) return <LoadingState msg="Carregando workflows..." />;
  if (error) return <ErrorState msg={error} />;

  const list = workflows || [];
  const tmplList = templates || [];

  return (
    <div className="fade-up">
      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        <MetricBox label="Workflows" value={list.length} unit="total" />
        <MetricBox label="Execuções" value={stats?.total_runs ?? "—"} unit="total" color="var(--success)" />
        <MetricBox label="Taxa de Sucesso" value={stats ? `${stats.success_rate}` : "—"} unit="%" color="var(--info)" />
        <MetricBox label="Duração Média" value={stats?.avg_duration_ms ? `${(stats.avg_duration_ms / 1000).toFixed(1)}` : "—"} unit="s" color="var(--warning)" />
      </div>

      {tmplList.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 11, color: "var(--muted)", fontFamily: "var(--mono)", letterSpacing: 1.5, textTransform: "uppercase", fontWeight: 500, marginBottom: 10 }}>
            Templates
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 10 }}>
            {tmplList.map(t => (
              <div key={t.slug} style={{ padding: "14px 16px", background: "var(--surface)", borderRadius: 8, border: "1px solid var(--border)", display: "flex", gap: 12, alignItems: "flex-start" }}>
                <div style={{ fontSize: 22, flexShrink: 0, marginTop: 2 }}>{CATEGORY_ICONS[t.category] || "📋"}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 3 }}>{t.name}</div>
                  <div style={{ fontSize: 10, color: "var(--muted)", lineHeight: 1.5, marginBottom: 8 }}>{t.description}</div>
                  <button
                    onClick={() => handleUseTemplate(t.slug)}
                    disabled={!!creatingTemplate}
                    style={{ padding: "4px 12px", background: "var(--accent-dim)", border: "1px solid var(--accent)40", borderRadius: 5, color: "var(--accent)", cursor: creatingTemplate ? "default" : "pointer", fontSize: 10, fontFamily: "var(--mono)", fontWeight: 600 }}
                  >
                    {creatingTemplate === t.slug ? "Criando..." : "Usar template →"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {list.length === 0 ? (
        <div style={{ padding: 60, textAlign: "center", color: "var(--muted)" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>🔧</div>
          <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 6, color: "var(--fg)" }}>Nenhum workflow ainda</p>
          <p style={{ fontSize: 12 }}>Crie seu primeiro ou use um template acima.</p>
        </div>
      ) : (
        <>
          <div style={{ fontSize: 11, color: "var(--muted)", fontFamily: "var(--mono)", letterSpacing: 1.5, textTransform: "uppercase", fontWeight: 500, marginBottom: 10 }}>
            Meus Workflows
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 14 }}>
            {list.map(wf => {
              const st = WORKFLOW_STATUS[wf.status] || WORKFLOW_STATUS.draft;
              return (
                <div
                  key={wf.id}
                  onClick={() => onSelect(wf)}
                  style={{ padding: "18px 20px", background: "var(--surface)", borderRadius: 10, border: "1px solid var(--border)", cursor: "pointer", transition: "all 0.2s" }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--accent)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.transform = "none"; }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 600 }}>{wf.name}</h3>
                    <Badge text={st.label} color={st.color} bg={st.bg} />
                  </div>
                  <p style={{ fontSize: 11, color: "var(--muted)", marginBottom: 12, lineHeight: 1.5 }}>{wf.description || "Sem descrição"}</p>
                  <div style={{ display: "flex", gap: 8, marginBottom: 12, fontSize: 10, color: "var(--muted)", fontFamily: "var(--mono)" }}>
                    <span>{wf.node_count || 0} nós</span>
                    <span style={{ color: "var(--border)" }}>·</span>
                    <span>{wf.run_count || 0} execuções</span>
                    <span style={{ color: "var(--border)" }}>·</span>
                    <span>v{wf.version}</span>
                  </div>
                  {wf.tags?.length > 0 && (
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                      {wf.tags.map(t => (
                        <span key={t} style={{ padding: "2px 8px", borderRadius: 3, fontSize: 9, fontFamily: "var(--mono)", color: "var(--accent)", background: "var(--accent-dim)", letterSpacing: 0.5 }}>{t}</span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
