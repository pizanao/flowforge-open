import {useState} from "react";

import {useAuth} from "../hooks/useAuth";

export function LoginPage({oauthLoading = false, oauthError = ""}) {
    const {
        login,
        beginGoogleOAuth,
        beginGitHubOAuth,
        oauthEnabled,
    } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const submit = async (event) => {
        event.preventDefault();
        setLoading(true);
        setError("");
        try {
            await login(email, password);
        } catch (err) {
            setError(err.message || "Falha ao autenticar.");
        } finally {
            setLoading(false);
        }
    };

    const startOAuth = (provider) => {
        setError("");
        try {
            if (provider === "google") {
                beginGoogleOAuth();
                return;
            }
            beginGitHubOAuth();
        } catch (err) {
            setError(err.message || "Falha ao iniciar OAuth.");
        }
    };

    const activeError = error || oauthError;

    return (
        <div style={{
            minHeight: "calc(100vh - 120px)",
            display: "grid",
            placeItems: "center",
            padding: "32px 0 48px",
        }}>
            <div style={{
                width: "100%",
                maxWidth: 440,
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: 32,
                boxShadow: "0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.08)",
            }}>
                <div style={{display: "flex", alignItems: "center", gap: 14, marginBottom: 18}}>
                    <div style={{
                        width: 38,
                        height: 38,
                        borderRadius: 10,
                        background: "var(--accent-dim)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        border: "1px solid var(--accent)30",
                        fontSize: 18
                    }}>🔐
                    </div>
                    <div>
                        <h1 style={{fontSize: 17, fontWeight: 700, letterSpacing: -0.3}}>FlowForge</h1>
                        <p style={{fontSize: 11, color: "var(--muted)", fontFamily: "var(--mono)"}}>Visual Workflow
                            Builder</p>
                    </div>
                </div>


                <form onSubmit={submit} style={{display: "grid", gap: 14}}>
                    <label style={{display: "grid", gap: 6}}>
            <span style={{fontSize: 11, color: "var(--muted)", letterSpacing: 1.2, textTransform: "uppercase"}}>
              Email
            </span>
                        <input
                            value={email}
                            onChange={(event) => setEmail(event.target.value)}
                            type="email"
                            autoComplete="email"
                            placeholder="Informe seu email"
                            style={{
                                height: 46,
                                borderRadius: 10,
                                border: "1px solid var(--border)",
                                background: "var(--surface2)",
                                color: "var(--fg)",
                                padding: "0 14px",
                                fontSize: 14,
                                fontFamily: "var(--font)",
                                outline: "none",
                            }}
                        />
                    </label>

                    <label style={{display: "grid", gap: 6}}>
            <span style={{fontSize: 11, color: "var(--muted)", letterSpacing: 1.2, textTransform: "uppercase"}}>
              Senha
            </span>
                        <input
                            value={password}
                            onChange={(event) => setPassword(event.target.value)}
                            type="password"
                            autoComplete="current-password"
                            placeholder="Informe sua senha"
                            style={{
                                height: 46,
                                borderRadius: 10,
                                border: "1px solid var(--border)",
                                background: "var(--surface2)",
                                color: "var(--fg)",
                                padding: "0 14px",
                                fontSize: 14,
                                fontFamily: "var(--font)",
                                outline: "none",
                            }}
                        />
                    </label>

                    {activeError && (
                        <div style={{
                            padding: "10px 12px",
                            borderRadius: 10,
                            border: "1px solid var(--danger)",
                            background: "color-mix(in srgb, var(--danger) 12%, transparent)",
                            color: "var(--danger)",
                            fontSize: 12,
                            lineHeight: 1.5,
                        }}>
                            {activeError}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading || oauthLoading}
                        style={{
                            height: 48,
                            borderRadius: 12,
                            border: "none",
                            background: "linear-gradient(135deg, var(--accent), #5f217e)",
                            color: "#fff",
                            fontWeight: 700,
                            fontSize: 14,
                            cursor: loading || oauthLoading ? "default" : "pointer",
                        }}
                    >
                        {loading ? "Entrando..." : "Entrar"}
                    </button>
                </form>

                <div style={{
                    margin: "22px 0 18px",
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    color: "var(--muted)",
                    fontSize: 11,
                    fontFamily: "var(--mono)",
                    textTransform: "uppercase",
                    letterSpacing: 1.2,
                }}>
                    <div style={{height: 1, flex: 1, background: "var(--border)"}}/>
                    <span>ou</span>
                    <div style={{height: 1, flex: 1, background: "var(--border)"}}/>
                </div>

                <div style={{display: "grid", gap: 10}}>
                    <button
                        type="button"
                        onClick={() => startOAuth("google")}
                        disabled={oauthLoading || !oauthEnabled.google}
                        style={{
                            height: 46,
                            borderRadius: 10,
                            border: "1px solid var(--border)",
                            background: "var(--surface)",
                            color: "var(--fg)",
                            cursor: oauthLoading || !oauthEnabled.google ? "default" : "pointer",
                            fontSize: 13,
                            fontWeight: 600,
                        }}
                    >
                        Continuar com Google
                    </button>
                    <button
                        type="button"
                        onClick={() => startOAuth("github")}
                        disabled={oauthLoading || !oauthEnabled.github}
                        style={{
                            height: 46,
                            borderRadius: 10,
                            border: "1px solid var(--border)",
                            background: "var(--surface)",
                            color: "var(--fg)",
                            cursor: oauthLoading || !oauthEnabled.github ? "default" : "pointer",
                            fontSize: 13,
                            fontWeight: 600,
                        }}
                    >
                        Continuar com GitHub
                    </button>
                </div>

                {oauthLoading && (
                    <p style={{marginTop: 16, color: "var(--muted)", fontSize: 12, fontFamily: "var(--mono)"}}>
                        Finalizando callback OAuth...
                    </p>
                )}
            </div>
        </div>
    );
}
