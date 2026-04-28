/**
 * Funções utilitárias e constantes do FlowForge.
 */

export function formatDate(isoString) {
  if (!isoString) return "—";
  return new Date(isoString).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

export function formatDuration(ms) {
  if (!ms) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * Configuração visual de cada tipo de nó.
 */
export const NODE_TYPES = {
  trigger:   { label: "Trigger",   icon: "⚡", color: "#a855f7", desc: "Ponto de entrada" },
  http:      { label: "HTTP",      icon: "🌐", color: "#3b82f6", desc: "Requisição HTTP" },
  transform: { label: "Transform", icon: "🔄", color: "#f59e0b", desc: "Transformar dados" },
  condition: { label: "Condição",  icon: "🔀", color: "#ef4444", desc: "Branch if/else" },
  llm:       { label: "LLM Agent", icon: "🤖", color: "#10b981", desc: "Claude API" },
  email:     { label: "Email",     icon: "📧", color: "#ec4899", desc: "Enviar email" },
  delay:     { label: "Delay",     icon: "⏱",  color: "#6b7280", desc: "Aguardar tempo" },
  output:    { label: "Output",    icon: "📤", color: "#8b5cf6", desc: "Resultado final" },
  telegram:  { label: "Telegram",  icon: "✈️", color: "#29b6f6", desc: "Enviar mensagem" },
  whatsapp:  { label: "WhatsApp",  icon: "💬", color: "#25d366", desc: "WhatsApp via Waha" },
};

/**
 * Status de execução com cores.
 */
export const RUN_STATUS = {
  pending:   { color: "#6b7280", bg: "#6b728015", label: "Pendente" },
  running:   { color: "#3b82f6", bg: "#3b82f615", label: "Executando" },
  success:   { color: "#10b981", bg: "#10b98115", label: "Sucesso" },
  failed:    { color: "#ef4444", bg: "#ef444415", label: "Falhou" },
  cancelled: { color: "#f59e0b", bg: "#f59e0b15", label: "Cancelado" },
};

export const WORKFLOW_STATUS = {
  draft:    { color: "#6b7280", bg: "#6b728015", label: "Rascunho" },
  active:   { color: "#10b981", bg: "#10b98115", label: "Ativo" },
  paused:   { color: "#f59e0b", bg: "#f59e0b15", label: "Pausado" },
  archived: { color: "#ef4444", bg: "#ef444415", label: "Arquivado" },
};
