import type { Ticket } from "../types";

interface Props {
  tickets: Ticket[];
  loading: boolean;
  error: string | null;
  selectedId: number | null;
  runningId: number | null;
  onSelect: (id: number) => void;
  onRun: (id: number) => void;
}

function subjectLine(t: Ticket): string {
  if (t.sku && t.size && t.qty) return `${t.qty} × ${t.sku} (${t.size})`;
  if (t.lease_id) return "Lease / rent obligation";
  return t.subject;
}

export function TicketQueue({ tickets, loading, error, selectedId, runningId, onSelect, onRun }: Props) {
  return (
    <section className="panel ticket-queue" aria-label="Ticket queue">
      <h2 className="panel-title">Ticket Queue</h2>
      {loading && <p className="muted">Loading tickets…</p>}
      {error && <p className="error-text">{error}</p>}
      {!loading && !error && tickets.length === 0 && <p className="muted">No tickets found.</p>}
      <ul className="ticket-list">
        {tickets.map((t) => {
          const isSelected = t.id === selectedId;
          const isRunning = t.id === runningId;
          const resolved = t.status === "resolved";
          return (
            <li
              key={t.id}
              className={`ticket-card ${isSelected ? "ticket-card--selected" : ""} ${resolved ? "ticket-card--resolved" : ""}`}
            >
              <button className="ticket-card__main" onClick={() => onSelect(t.id)}>
                <div className="ticket-card__top">
                  <span className="ticket-card__id">#{t.id}</span>
                  <span className={`status-pill status-pill--${resolved ? "resolved" : "open"}`}>
                    {resolved ? "Resolved" : "Open"}
                  </span>
                </div>
                <div className="ticket-card__subject">{t.subject}</div>
                <div className="ticket-card__detail">{subjectLine(t)}</div>
                <div className="ticket-card__requester">{t.requester}</div>
              </button>
              <button
                className={`btn btn--block ${resolved ? "btn--gold" : "btn--primary"}`}
                disabled={runningId !== null}
                onClick={() => onRun(t.id)}
                title={resolved ? "This ticket is already resolved — re-running will ask for confirmation." : undefined}
              >
                {isRunning ? "Running…" : resolved ? "Re-run (resolved)" : "Run agent team"}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
