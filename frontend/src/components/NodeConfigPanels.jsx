/**
 * Painéis de configuração por tipo de nó.
 * NodeConfigPanel faz dispatch para o painel correto conforme node.node_type.
 */

const inputStyle = {
  width: "100%", padding: "6px 10px", background: "var(--bg)",
  border: "1px solid var(--border)", borderRadius: 5, color: "var(--fg)",
  fontSize: 12, fontFamily: "var(--font)", boxSizing: "border-box",
  outline: "none",
};

const selectStyle = { ...inputStyle, cursor: "pointer" };

const textareaStyle = {
  ...inputStyle,
  resize: "vertical", minHeight: 72, lineHeight: 1.5, fontFamily: "var(--mono)",
};

function Field({ label, children, hint }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{
        fontSize: 10, color: "var(--muted)", fontFamily: "var(--mono)",
        letterSpacing: 1, textTransform: "uppercase", display: "block", marginBottom: 4,
      }}>
        {label}
      </label>
      {children}
      {hint && <div style={{ fontSize: 10, color: "var(--muted)", marginTop: 3 }}>{hint}</div>}
    </div>
  );
}

// ── Trigger ──────────────────────────────────────────────────────────────────
function TriggerPanel({ config, onChange, workflowId }) {
  const tt = config.trigger_type || "manual";
  const webhookUrl = workflowId
    ? `${window.location.protocol}//${window.location.hostname}:8006/api/workflows/${workflowId}/webhook/`
    : null;

  const copyWebhookUrl = () => {
    if (webhookUrl) navigator.clipboard.writeText(webhookUrl);
  };

  return (
    <>
      <Field label="Tipo de disparo">
        <select
          aria-label="Tipo de disparo"
          style={selectStyle}
          value={tt}
          onChange={e => onChange({ ...config, trigger_type: e.target.value })}
        >
          <option value="manual">Manual</option>
          <option value="webhook">Webhook (HTTP POST externo)</option>
          <option value="schedule">Agendado (cron)</option>
        </select>
      </Field>

      {tt === "webhook" && webhookUrl && (
        <Field label="URL do Webhook" hint="Envie um POST para esta URL com o payload no body">
          <div style={{ display: "flex", gap: 4 }}>
            <input
              readOnly
              style={{ ...inputStyle, flex: 1, color: "var(--muted)", fontFamily: "var(--mono)", fontSize: 10 }}
              value={webhookUrl}
            />
            <button
              onClick={copyWebhookUrl}
              title="Copiar URL"
              style={{ padding: "6px 10px", background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--fg)", cursor: "pointer", fontSize: 11, flexShrink: 0 }}
            >
              📋
            </button>
          </div>
          <div style={{ marginTop: 10, padding: "10px 12px", background: "var(--bg)", borderRadius: 6, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: 10, color: "var(--muted)", fontFamily: "var(--mono)", letterSpacing: 1, textTransform: "uppercase", marginBottom: 6 }}>Exemplo (curl)</div>
            <pre style={{ margin: 0, fontSize: 10, fontFamily: "var(--mono)", color: "var(--fg)", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
{`curl -X POST \\
  ${webhookUrl} \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Olá!", "from": "5511999999999"}'`}
            </pre>
          </div>
        </Field>
      )}

      {tt === "schedule" && (
        <Field label="Expressão cron" hint="Ex: 0 9 * * 1-5 (dias úteis às 9h)">
          <input
            style={inputStyle}
            value={config.schedule || ""}
            placeholder="0 * * * *"
            onChange={e => onChange({ ...config, schedule: e.target.value })}
          />
        </Field>
      )}
    </>
  );
}

// ── HTTP ─────────────────────────────────────────────────────────────────────
function HttpPanel({ config, onChange }) {
  const headers = config.headers || {};
  const headerEntries = Object.entries(headers);

  const setHeader = (idx, key, value) => {
    const entries = [...headerEntries];
    entries[idx] = [key, value];
    onChange({ ...config, headers: Object.fromEntries(entries) });
  };

  const addHeader = () => {
    onChange({ ...config, headers: { ...headers, "": "" } });
  };

  const removeHeader = (idx) => {
    const entries = headerEntries.filter((_, i) => i !== idx);
    onChange({ ...config, headers: Object.fromEntries(entries) });
  };

  return (
    <>
      <Field label="Método">
        <select
          aria-label="Método"
          style={selectStyle}
          value={config.method || "GET"}
          onChange={e => onChange({ ...config, method: e.target.value })}
        >
          {["GET", "POST", "PUT", "PATCH", "DELETE"].map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </Field>
      <Field label="URL" hint="Use {{variavel}} para interpolação">
        <input
          aria-label="URL"
          style={inputStyle}
          value={config.url || ""}
          placeholder="https://api.exemplo.com/dados"
          onChange={e => onChange({ ...config, url: e.target.value })}
        />
      </Field>
      <Field label="Headers">
        {headerEntries.map(([k, v], idx) => (
          <div key={idx} style={{ display: "flex", gap: 4, marginBottom: 4 }}>
            <input
              style={{ ...inputStyle, flex: 1 }}
              value={k}
              placeholder="chave"
              onChange={e => setHeader(idx, e.target.value, v)}
            />
            <input
              style={{ ...inputStyle, flex: 2 }}
              value={v}
              placeholder="valor"
              onChange={e => setHeader(idx, k, e.target.value)}
            />
            <button
              onClick={() => removeHeader(idx)}
              style={{ padding: "0 8px", background: "transparent", border: "1px solid var(--border)", borderRadius: 5, color: "var(--muted)", cursor: "pointer", fontSize: 12 }}
            >×</button>
          </div>
        ))}
        <button
          onClick={addHeader}
          style={{ padding: "4px 10px", background: "transparent", border: "1px dashed var(--border)", borderRadius: 5, color: "var(--muted)", cursor: "pointer", fontSize: 11, width: "100%" }}
        >+ Adicionar header</button>
      </Field>
      <Field label="Body (JSON)" hint="Apenas para POST/PUT/PATCH">
        <textarea
          style={textareaStyle}
          value={typeof config.body === "string" ? config.body : JSON.stringify(config.body || {}, null, 2)}
          placeholder="{}"
          onChange={e => {
            try { onChange({ ...config, body: JSON.parse(e.target.value) }); }
            catch { onChange({ ...config, body: e.target.value }); }
          }}
        />
      </Field>
    </>
  );
}

// ── Transform ─────────────────────────────────────────────────────────────────
function TransformPanel({ config, onChange }) {
  const op = config.operation || "passthrough";
  const params = config.params || {};

  const opLabels = {
    passthrough: "Passthrough (sem alteração)",
    pick: "Pick (selecionar campos)",
    rename: "Rename (renomear campos)",
    merge: "Merge (combinar inputs)",
    map: "Map (transformar cada item)",
    flatten: "Flatten (achatar lista)",
  };

  return (
    <>
      <Field label="Operação">
        <select
          style={selectStyle}
          value={op}
          onChange={e => onChange({ ...config, operation: e.target.value, params: {} })}
        >
          {Object.entries(opLabels).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
      </Field>

      {op === "pick" && (
        <Field label="Campos (um por linha)">
          <textarea
            style={textareaStyle}
            value={(params.keys || []).join("\n")}
            placeholder={"nome\nidade\nemail"}
            onChange={e => onChange({ ...config, params: { keys: e.target.value.split("\n").filter(Boolean) } })}
          />
        </Field>
      )}

      {op === "rename" && (
        <Field label="Mapeamento (antigo → novo, um por linha)" hint="Ex: firstName → nome">
          <textarea
            style={textareaStyle}
            value={Object.entries(params.mapping || {}).map(([k, v]) => `${k} → ${v}`).join("\n")}
            placeholder={"firstName → nome\nlastName → sobrenome"}
            onChange={e => {
              const mapping = {};
              e.target.value.split("\n").forEach(line => {
                const [from, to] = line.split("→").map(s => s.trim());
                if (from && to) mapping[from] = to;
              });
              onChange({ ...config, params: { mapping } });
            }}
          />
        </Field>
      )}
    </>
  );
}

// ── Condition ─────────────────────────────────────────────────────────────────
function ConditionPanel({ config, onChange }) {
  const operators = [
    { value: "eq", label: "= igual a" },
    { value: "neq", label: "≠ diferente de" },
    { value: "gt", label: "> maior que" },
    { value: "lt", label: "< menor que" },
    { value: "gte", label: "≥ maior ou igual" },
    { value: "lte", label: "≤ menor ou igual" },
    { value: "contains", label: "contém" },
    { value: "exists", label: "existe (não nulo)" },
  ];

  return (
    <>
      <Field label="Campo" hint="Ex: data.status ou user.age">
        <input
          style={inputStyle}
          value={config.field || ""}
          placeholder="data.campo"
          onChange={e => onChange({ ...config, field: e.target.value })}
        />
      </Field>
      <Field label="Operador">
        <select
          style={selectStyle}
          value={config.operator || "eq"}
          onChange={e => onChange({ ...config, operator: e.target.value })}
        >
          {operators.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </Field>
      {config.operator !== "exists" && (
        <Field label="Valor">
          <input
            style={inputStyle}
            value={config.value ?? ""}
            placeholder="valor esperado"
            onChange={e => onChange({ ...config, value: e.target.value })}
          />
        </Field>
      )}
    </>
  );
}

// ── LLM ──────────────────────────────────────────────────────────────────────
function LLMPanel({ config, onChange }) {
  return (
    <>
      <Field label="Modelo">
        <input
          aria-label="Modelo"
          style={inputStyle}
          value={config.model || "claude-sonnet-4-20250514"}
          placeholder="claude-sonnet-4-20250514"
          onChange={e => onChange({ ...config, model: e.target.value })}
        />
      </Field>
      <Field label="Template do prompt" hint="Use {{data}} para injetar o input do nó anterior">
        <textarea
          aria-label="Template do prompt"
          style={{ ...textareaStyle, minHeight: 100 }}
          value={config.prompt_template || ""}
          placeholder="Analise os seguintes dados e retorne um resumo:\n\n{{data}}"
          onChange={e => onChange({ ...config, prompt_template: e.target.value })}
        />
      </Field>
    </>
  );
}

// ── Email ─────────────────────────────────────────────────────────────────────
function EmailPanel({ config, onChange }) {
  return (
    <>
      <Field label="Para (destinatário)">
        <input
          style={inputStyle}
          value={config.to || ""}
          placeholder="usuario@exemplo.com"
          onChange={e => onChange({ ...config, to: e.target.value })}
        />
      </Field>
      <Field label="Assunto" hint="Use {{variavel}} para interpolação">
        <input
          style={inputStyle}
          value={config.subject || ""}
          placeholder="Notificação FlowForge"
          onChange={e => onChange({ ...config, subject: e.target.value })}
        />
      </Field>
      <Field label="Corpo do email" hint="Use {{variavel}} para interpolação">
        <textarea
          style={textareaStyle}
          value={config.body_template || ""}
          placeholder="Olá, o workflow foi concluído.\n\nDados: {{data}}"
          onChange={e => onChange({ ...config, body_template: e.target.value })}
        />
      </Field>
    </>
  );
}

// ── Delay ─────────────────────────────────────────────────────────────────────
function DelayPanel({ config, onChange }) {
  const seconds = config.seconds ?? 1;
  return (
    <Field label={`Aguardar ${seconds} segundo${seconds !== 1 ? "s" : ""}`}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <input
          type="range"
          min={1} max={60} step={1}
          value={seconds}
          onChange={e => onChange({ ...config, seconds: Number(e.target.value) })}
          style={{ flex: 1, accentColor: "var(--accent)", cursor: "pointer" }}
        />
        <input
          type="number"
          min={1} max={300}
          value={seconds}
          onChange={e => onChange({ ...config, seconds: Math.max(1, Number(e.target.value)) })}
          style={{ ...inputStyle, width: 64, textAlign: "center" }}
        />
      </div>
      <div style={{ fontSize: 10, color: "var(--muted)", marginTop: 4 }}>Máximo: 300s em produção</div>
    </Field>
  );
}

// ── Output ────────────────────────────────────────────────────────────────────
function OutputPanel({ config, onChange }) {
  return (
    <Field label="Formato de saída">
      <select
        style={selectStyle}
        value={config.format || "raw"}
        onChange={e => onChange({ ...config, format: e.target.value })}
      >
        <option value="raw">Raw (dados completos)</option>
        <option value="summary">Summary (resumo textual)</option>
      </select>
    </Field>
  );
}

// ── Telegram ──────────────────────────────────────────────────────────────────
function TelegramPanel({ config, onChange }) {
  return (
    <>
      <Field label="Mensagem" hint="Use {{response}} para injetar o output do nó anterior">
        <textarea
          style={{ ...textareaStyle, minHeight: 88 }}
          value={config.text || "{{response}}"}
          placeholder="{{response}}"
          onChange={e => onChange({ ...config, text: e.target.value })}
        />
      </Field>
      <Field label="Modo de formatação">
        <select
          style={selectStyle}
          value={config.parse_mode || "Markdown"}
          onChange={e => onChange({ ...config, parse_mode: e.target.value })}
        >
          <option value="Markdown">Markdown</option>
          <option value="MarkdownV2">MarkdownV2</option>
          <option value="HTML">HTML</option>
        </select>
      </Field>
      <Field label="Chat ID (opcional)" hint="Deixe vazio para usar TELEGRAM_CHAT_ID do .env">
        <input
          style={inputStyle}
          value={config.chat_id || ""}
          placeholder="Padrão: TELEGRAM_CHAT_ID do .env"
          onChange={e => onChange({ ...config, chat_id: e.target.value })}
        />
      </Field>
    </>
  );
}

function WhatsAppPanel({ config, onChange }) {
  return (
    <>
      <Field label="Telefone" hint="Número com DDI+DDD, ex: 5511999999999">
        <input
          style={inputStyle}
          value={config.phone || ""}
          placeholder="5511999999999"
          onChange={e => onChange({ ...config, phone: e.target.value })}
        />
      </Field>
      <Field label="Mensagem" hint="Use {{response}} para injetar o output do nó anterior">
        <textarea
          style={{ ...textareaStyle, minHeight: 88 }}
          value={config.text || "{{response}}"}
          placeholder="{{response}}"
          onChange={e => onChange({ ...config, text: e.target.value })}
        />
      </Field>
      <Field label="Sessão Waha (opcional)" hint="Deixe vazio para usar a sessão padrão do .env">
        <input
          style={inputStyle}
          value={config.session || ""}
          placeholder="Padrão: WAHA_DEFAULT_SESSION do .env"
          onChange={e => onChange({ ...config, session: e.target.value })}
        />
      </Field>
    </>
  );
}

// ── Dispatcher ────────────────────────────────────────────────────────────────
const PANELS = {
  trigger: TriggerPanel,
  http: HttpPanel,
  transform: TransformPanel,
  condition: ConditionPanel,
  llm: LLMPanel,
  email: EmailPanel,
  delay: DelayPanel,
  output: OutputPanel,
  telegram: TelegramPanel,
  whatsapp: WhatsAppPanel,
};

export function NodeConfigPanel({ node, workflowId, onChange }) {
  const Panel = PANELS[node.node_type];
  if (!Panel) {
    return (
      <div style={{ fontSize: 12, color: "var(--muted)", textAlign: "center", padding: "20px 0" }}>
        Sem configuração para este tipo de nó.
      </div>
    );
  }
  return (
    <Panel
      config={node.config || {}}
      workflowId={workflowId}
      onChange={(newConfig) => onChange(node.id, newConfig)}
    />
  );
}
