import { useCallback, useEffect, useState } from "react";

import { LoginPage } from "./components/LoginPage";
import { ThemeToggle } from "./components/ThemeToggle";
import { apiFetch } from "./hooks/useApi";
import { clearPendingOAuthContext, getPendingOAuthContext, useAuth } from "./hooks/useAuth";
import { useWorkflowRun } from "./hooks/useWorkflowRun";
import { WorkflowListPage } from "./pages/WorkflowListPage";
import { WorkflowEditorPage } from "./pages/WorkflowEditorPage";

const css = `
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: var(--font); background: var(--bg); color: var(--fg); }
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
  @keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes pulse { 0%, 100% { box-shadow: 0 0 8px #a855f740; } 50% { box-shadow: 0 0 20px #a855f780; } }
  .fade-up { animation: fadeUp .3s ease-out both; }
  button { font-family: var(--font); }
`;

export default function App() {
  const { isAuthenticated, loginWithGoogle, loginWithGitHub, logout } = useAuth();
  const [view, setView] = useState("list");
  const [selectedId, setSelectedId] = useState(null);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [oauthError, setOauthError] = useState("");

  const { startRun, reset: resetRun, runStatus, nodeStates, progress, selectedNodeId, setSelectedNodeId } = useWorkflowRun(selectedId);

  const handleSelect = useCallback((wf) => { resetRun(); setSelectedId(wf.id); setView("detail"); }, [resetRun]);
  const handleBack = useCallback(() => { resetRun(); setView("list"); setSelectedId(null); }, [resetRun]);

  useEffect(() => {
    if (!isAuthenticated) { resetRun(); setView("list"); setSelectedId(null); }
  }, [isAuthenticated, resetRun]);

  useEffect(() => {
    if (isAuthenticated) return;
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const error = params.get("error");
    if (!code && !error) return;

    const finish = async () => {
      const pending = getPendingOAuthContext();
      const state = params.get("state");
      setOauthLoading(true); setOauthError("");
      try {
        if (error) throw new Error(params.get("error_description") || "OAuth cancelado.");
        if (!pending.provider) throw new Error("Callback OAuth sem provider pendente.");
        if (!state || state !== pending.state) throw new Error("State OAuth inválido.");
        if (pending.provider === "google") await loginWithGoogle(code, pending.redirectUri);
        else await loginWithGitHub(code, pending.redirectUri);
        clearPendingOAuthContext();
        window.history.replaceState({}, document.title, window.location.pathname);
      } catch (err) {
        clearPendingOAuthContext();
        setOauthError(err.message || "Falha no callback OAuth.");
        window.history.replaceState({}, document.title, window.location.pathname);
      } finally { setOauthLoading(false); }
    };
    finish();
  }, [isAuthenticated, loginWithGoogle, loginWithGitHub]);

  const handleNewWorkflow = useCallback(async () => {
    try {
      const res = await apiFetch("/api/workflows/", { method: "POST", body: JSON.stringify({ name: "Novo Workflow", description: "", tags: [] }) });
      if (res.ok) handleSelect(await res.json());
    } catch {}
  }, [handleSelect]);

  const header = (
    <header style={{ padding: "18px 0", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 14, cursor: isAuthenticated ? "pointer" : "default" }} onClick={isAuthenticated ? handleBack : undefined}>
        <div style={{ width: 38, height: 38, borderRadius: 10, background: "var(--accent-dim)", display: "flex", alignItems: "center", justifyContent: "center", border: "1px solid var(--accent)30", fontSize: 18 }}>🔧</div>
        <div>
          <h1 style={{ fontSize: 17, fontWeight: 700, letterSpacing: -0.3 }}>FlowForge</h1>
          <p style={{ fontSize: 11, color: "var(--muted)", fontFamily: "var(--mono)" }}>Visual Workflow Builder</p>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {isAuthenticated && view === "list" && (
          <button onClick={handleNewWorkflow} style={{ padding: "8px 18px", background: "var(--accent)", border: "none", borderRadius: 6, color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>+ Novo Workflow</button>
        )}
        <ThemeToggle />
        {isAuthenticated && (
          <button onClick={logout} style={{ padding: "8px 18px", background: "transparent", border: "1px solid var(--border)", borderRadius: 6, color: "var(--fg)", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>Sair</button>
        )}
      </div>
    </header>
  );

  return (
    <>
      <style>{css}</style>
      <div style={{ minHeight: "100vh", maxWidth: 1100, margin: "0 auto", padding: "0 24px" }}>
        {header}

        {!isAuthenticated && <LoginPage oauthLoading={oauthLoading} oauthError={oauthError} />}

        {isAuthenticated && view === "list" && <WorkflowListPage onSelect={handleSelect} />}

        {isAuthenticated && view === "detail" && selectedId && (
          <WorkflowEditorPage
            workflowId={selectedId} onBack={handleBack}
            nodeStates={nodeStates} onNodeClick={setSelectedNodeId}
            selectedNodeId={selectedNodeId} onCloseDrawer={() => setSelectedNodeId(null)}
            runStatus={runStatus} progress={progress}
            onRun={(saveFirst) => { saveFirst?.(); startRun(); }}
          />
        )}

        {isAuthenticated && (
          <footer style={{ padding: "20px 0", marginTop: 32, borderTop: "1px solid var(--border)", color: "var(--muted)", fontSize: 10, display: "flex", justifyContent: "space-between" }}>
            <span>Stack: Django 5.x + Celery + Django Channels + React</span>
            <span>Daniel Pizani · FlowForge · 2026</span>
          </footer>
        )}
      </div>
    </>
  );
}
