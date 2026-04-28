import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { NODE_TYPES } from "../../utils/formatters";

export function DurationChart({ runs }) {
  const data = runs.flatMap(r =>
    (r.node_executions || [])
      .filter(n => n.status === "success" && n.duration_ms > 0)
      .map(n => ({ name: n.node_label, duration: n.duration_ms, type: n.node_type }))
  );

  if (!data.length) {
    return (
      <div style={{ padding: 20, textAlign: "center", color: "var(--muted)", fontSize: 12 }}>
        Sem dados de performance ainda.
      </div>
    );
  }

  return (
    <div style={{ padding: "16px", background: "var(--surface)", borderRadius: 10, border: "1px solid var(--border)" }}>
      <div style={{ fontSize: 10, color: "var(--muted)", marginBottom: 10, letterSpacing: 1.5, textTransform: "uppercase", fontWeight: 500 }}>
        Duração por nó (ms)
      </div>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <XAxis dataKey="name" tick={{ fontSize: 9, fill: "#7878a0" }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize: 9, fill: "#7878a0" }} tickLine={false} axisLine={false} />
          <Tooltip
            contentStyle={{ background: "#111119", border: "1px solid #26263a", borderRadius: 6, fontSize: 11, fontFamily: "'Cascadia Code', monospace" }}
            formatter={(v) => [`${v}ms`, "Duração"]}
          />
          <Bar dataKey="duration" radius={[4, 4, 0, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={(NODE_TYPES[d.type] || NODE_TYPES.trigger).color + "cc"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
