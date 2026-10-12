import { AGENT_META } from "../agentMeta";
import type { AgentRole } from "../types";

const ROSTER: AgentRole[] = ["boss", "inventory", "accounting", "facilities", "customer_service"];

export function AgentRoster() {
  return (
    <section className="panel agent-roster" aria-label="Agent roster">
      <h2 className="panel-title">Agent Roster</h2>
      <ul className="roster-list">
        {ROSTER.map((role) => {
          const meta = AGENT_META[role];
          return (
            <li key={role} className="roster-item">
              <span className="roster-badge" style={{ background: meta.color }}>
                {meta.short}
              </span>
              <div>
                <div className="roster-name">{meta.label}</div>
                <div className="roster-desc">{meta.description}</div>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
