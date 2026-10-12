import type { AuditEvent, Ticket } from "../types";
import { AGENT_META } from "../agentMeta";
import type { RunGroup } from "../runGrouping";

interface Props {
  ticket: Ticket | null;
  /** True only while a brand-new run's events are streaming in via polling.
   * These are shown separately from, and never mixed into, historical runs. */
  isLive: boolean;
  liveEvents: AuditEvent[];
  liveError: string | null;
  /** Historical runs for this ticket, most recent first. Populated once the
   * ticket is selected (and refreshed after a run completes). */
  runGroups: RunGroup[];
  selectedRunId: string | null;
  onSelectRun: (runId: string) => void;
  /** System-initiated events (ticket closure, recorded approvals) that have
   * no genuine agent-run association -- shown as ticket-level actions. */
  systemEvents: AuditEvent[];
}

function eventLine(e: AuditEvent): string {
  switch (e.event_type) {
    case "agent_start":
      return "started working";
    case "agent_end":
      return "finished its part";
    case "delegation": {
      const to = (e.detail.to_agent as string) ?? "?";
      const reason = (e.detail.reason as string) ?? "";
      return `delegated to ${AGENT_META[to as keyof typeof AGENT_META]?.label ?? to} — ${reason}`;
    }
    case "mcp_tool_call":
      return `called MCP tool \`${e.detail.tool}\``;
    case "approval_recorded":
      return `recorded a human approval (${(e.detail as { approval_id?: string }).approval_id ?? ""})`;
    case "reset":
      return "working database was reset";
    case "error":
      return `error: ${e.detail.error ?? "unknown error"}`;
    default:
      return e.event_type;
  }
}

function systemEventLine(e: AuditEvent): string {
  const tool = e.detail?.tool as string | undefined;
  if (tool === "close_ticket") return "Ticket closed (close_ticket)";
  if (e.event_type === "approval_recorded") {
    return `Payment approval recorded (approval_id ${(e.detail as { approval_id?: string }).approval_id ?? "?"})`;
  }
  if (tool) return `System action: ${tool}`;
  return `System: ${e.event_type}`;
}

function EventList({ events }: { events: AuditEvent[] }) {
  return (
    <ol className="timeline">
      {events.map((e, i) => {
        const meta = AGENT_META[e.agent] ?? AGENT_META.system;
        return (
          <li key={`${e.timestamp}-${i}`} className="timeline-item">
            <span className="timeline-dot" style={{ background: meta.color }} title={meta.label}>
              {meta.short}
            </span>
            <div className="timeline-body">
              <div className="timeline-header">
                <strong style={{ color: meta.color }}>{meta.label}</strong>
                <span className="timeline-time">{new Date(e.timestamp).toLocaleTimeString()}</span>
              </div>
              <div className="timeline-text">{eventLine(e)}</div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function AgentTimeline({
  ticket,
  isLive,
  liveEvents,
  liveError,
  runGroups,
  selectedRunId,
  onSelectRun,
  systemEvents,
}: Props) {
  const selectedRun = runGroups.find((g) => g.runId === selectedRunId) ?? null;

  return (
    <section className="panel agent-timeline" aria-label="Agent activity">
      <div className="panel-title-row">
        <h2 className="panel-title">Agent Activity</h2>
        {isLive && (
          <span className="live-badge" role="status">
            <span className="live-dot" /> Live — polling /events
          </span>
        )}
      </div>

      {!ticket && <p className="muted">Select a ticket to see its plan, then run the team to see real activity here.</p>}

      {ticket && (
        <>
          <div className="ticket-brief">
            <h3>
              Ticket #{ticket.id} — {ticket.subject}
            </h3>
            <p className="muted">{ticket.requester}</p>
            {(ticket.id === 101 || ticket.id === 103) && (
              <p className="approval-flag" style={{ marginTop: "0.5rem" }}>
                This ticket remains OPEN because finishing it requires an out-of-system human action
                (placing a vendor order, or getting the customer's real decision) that this system does
                not have a tool to perform. No customer communication or vendor order has occurred.
              </p>
            )}
          </div>

          {isLive && (
            <div className="run-live-block">
              <h3 style={{ marginBottom: "0.4rem" }}>Run in progress</h3>
              {liveError && <p className="error-text">{liveError}</p>}
              {liveEvents.length === 0 && !liveError && <p className="muted">Waiting for the first agent event…</p>}
              <EventList events={liveEvents} />
            </div>
          )}

          {!isLive && runGroups.length === 0 && (
            <p className="muted">No activity yet for this ticket. Click “Run agent team.”</p>
          )}

          {!isLive && runGroups.length > 0 && (
            <>
              <div className="run-selector-row">
                <label htmlFor="run-select" className="muted small">
                  Historical run ({runGroups.length} total, most recent first):
                </label>
                <select
                  id="run-select"
                  className="run-select"
                  value={selectedRunId ?? ""}
                  onChange={(e) => onSelectRun(e.target.value)}
                >
                  {runGroups.map((g, i) => (
                    <option key={g.runId} value={g.runId}>
                      {i === 0 ? "Most recent — " : ""}
                      {new Date(g.startedAt).toLocaleString()} ({g.events.length} events)
                    </option>
                  ))}
                </select>
              </div>

              {selectedRun && (
                <>
                  <EventList events={selectedRun.events} />
                  {selectedRun.finalSummary && (
                    <div className="ticket-summary">
                      <h3>Boss's Final Summary (this run)</h3>
                      <p>{selectedRun.finalSummary.summary}</p>
                      <h4>Recommendation</h4>
                      <p>{selectedRun.finalSummary.recommendation}</p>
                      {selectedRun.finalSummary.requires_human_approval && (
                        <p className="approval-flag">
                          ⚠ This run's recommendation requires human approval before any money moves or
                          the ticket can be considered truly resolved — a finished run is not the same as
                          a resolved business outcome.
                        </p>
                      )}
                    </div>
                  )}
                </>
              )}
            </>
          )}

          {systemEvents.length > 0 && (
            <div className="system-actions-block">
              <h3>Ticket-level system actions</h3>
              <p className="muted small">
                Not part of any agent run — these are backend actions triggered directly (e.g. a human
                approving a payment or closing a ticket), shown separately so they are never mistaken for
                agent activity.
              </p>
              <ol className="timeline">
                {systemEvents.map((e, i) => {
                  const meta = AGENT_META.system;
                  return (
                    <li key={`sys-${e.timestamp}-${i}`} className="timeline-item">
                      <span className="timeline-dot" style={{ background: meta.color }} title={meta.label}>
                        {meta.short}
                      </span>
                      <div className="timeline-body">
                        <div className="timeline-header">
                          <strong style={{ color: meta.color }}>System</strong>
                          <span className="timeline-time">{new Date(e.timestamp).toLocaleString()}</span>
                        </div>
                        <div className="timeline-text">{systemEventLine(e)}</div>
                      </div>
                    </li>
                  );
                })}
              </ol>
            </div>
          )}
        </>
      )}
    </section>
  );
}
