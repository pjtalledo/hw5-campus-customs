import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";
import { TicketQueue } from "./components/TicketQueue";
import { AgentTimeline } from "./components/AgentTimeline";
import { AgentRoster } from "./components/AgentRoster";
import { CashPanel } from "./components/CashPanel";
import { ApprovalsPanel } from "./components/ApprovalsPanel";
import * as api from "./api";
import { ApiRequestError } from "./api";
import { extractSystemEvents, groupEventsByRun } from "./runGrouping";
import type { RunGroup } from "./runGrouping";
import type { AuditEvent, CashAccount, PendingApproval, Ticket } from "./types";

const POLL_INTERVAL_MS = 1500;
// Full per-ticket history can span many runs (e.g. 84 events across 8 runs
// for one ticket during development) -- 500 matches the backend's own max.
const HISTORY_LIMIT = 500;

function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [ticketsLoading, setTicketsLoading] = useState(true);
  const [ticketsError, setTicketsError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [runningId, setRunningId] = useState<number | null>(null);

  // Historical events for the selected ticket, grouped by genuine run_id.
  const [runGroups, setRunGroups] = useState<RunGroup[]>([]);
  const [systemEvts, setSystemEvts] = useState<AuditEvent[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [historyLoadError, setHistoryLoadError] = useState<string | null>(null);

  // Events belonging only to a run currently in progress -- isolated from
  // history by timestamp, never mixed with prior runs.
  const [isLive, setIsLive] = useState(false);
  const [liveEvents, setLiveEvents] = useState<AuditEvent[]>([]);
  const [liveError, setLiveError] = useState<string | null>(null);
  const liveSinceTimestamp = useRef<string | null>(null);

  const [cash, setCash] = useState<CashAccount | null>(null);
  const [cashLoading, setCashLoading] = useState(true);
  const [cashError, setCashError] = useState<string | null>(null);
  const [cashPulse, setCashPulse] = useState(false);

  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [approvalsLoading, setApprovalsLoading] = useState(true);
  const [approvalsError, setApprovalsError] = useState<string | null>(null);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [approveError, setApproveError] = useState<string | null>(null);

  const [backendUp, setBackendUp] = useState(true);

  const pollHandle = useRef<number | null>(null);

  const refreshTickets = useCallback(async () => {
    setTicketsLoading(true);
    setTicketsError(null);
    try {
      const data = await api.getTickets();
      setTickets(data);
      setBackendUp(true);
    } catch (err) {
      const msg = err instanceof ApiRequestError ? err.message : "Unexpected error loading tickets.";
      setTicketsError(msg);
      if (err instanceof ApiRequestError && err.status === 0) setBackendUp(false);
    } finally {
      setTicketsLoading(false);
    }
  }, []);

  const refreshCash = useCallback(async () => {
    setCashLoading(true);
    setCashError(null);
    try {
      const data = await api.getCash();
      setCash(data);
    } catch (err) {
      setCashError(err instanceof ApiRequestError ? err.message : "Could not load the checking balance.");
    } finally {
      setCashLoading(false);
    }
  }, []);

  const refreshApprovals = useCallback(async () => {
    setApprovalsLoading(true);
    setApprovalsError(null);
    try {
      const data = await api.getApprovals("pending");
      setApprovals(data.approvals);
    } catch (err) {
      setApprovalsError(err instanceof ApiRequestError ? err.message : "Could not load pending approvals.");
    } finally {
      setApprovalsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshTickets();
    refreshCash();
    refreshApprovals();
  }, [refreshTickets, refreshCash, refreshApprovals]);

  const selectedTicket = tickets.find((t) => t.id === selectedId) ?? null;

  /** Loads and groups a ticket's full history. Never triggers an agent run. */
  async function loadHistory(id: number) {
    setHistoryLoadError(null);
    try {
      const data = await api.getEvents({ ticketId: id, limit: HISTORY_LIMIT });
      const groups = groupEventsByRun(data.events);
      setRunGroups(groups);
      setSystemEvts(extractSystemEvents(data.events));
      setSelectedRunId(groups.length > 0 ? groups[0].runId : null);
    } catch (err) {
      setHistoryLoadError(err instanceof ApiRequestError ? err.message : "Could not load this ticket's history.");
      setRunGroups([]);
      setSystemEvts([]);
      setSelectedRunId(null);
    }
  }

  function handleSelect(id: number) {
    // Selecting a ticket only reads its history. It never starts a run.
    setSelectedId(id);
    setLiveEvents([]);
    setLiveError(null);
    loadHistory(id);
  }

  async function handleRun(id: number) {
    if (runningId !== null) return; // defense in depth; the UI also disables this
    const ticket = tickets.find((t) => t.id === id);
    if (ticket?.status === "resolved") {
      const confirmed = window.confirm(
        `Ticket #${id} is already marked resolved. Re-running its agent team will make real model and MCP calls again. Continue?`
      );
      if (!confirmed) return;
    }

    setSelectedId(id);
    setRunningId(id);
    setLiveEvents([]);
    setLiveError(null);
    setIsLive(true);

    // Snapshot the latest known timestamp for this ticket so the live view
    // can isolate only events strictly after it -- never mixing in history.
    try {
      const snapshot = await api.getEvents({ ticketId: id, limit: 1 });
      liveSinceTimestamp.current = snapshot.events.length > 0 ? snapshot.events[snapshot.events.length - 1].timestamp : null;
    } catch {
      liveSinceTimestamp.current = null;
    }

    pollHandle.current = window.setInterval(async () => {
      try {
        const data = await api.getEvents({ ticketId: id, limit: HISTORY_LIMIT });
        const since = liveSinceTimestamp.current;
        const fresh = since ? data.events.filter((e) => e.timestamp > since) : data.events;
        setLiveEvents(fresh);
      } catch {
        // transient poll failure; keep trying until the run settles
      }
    }, POLL_INTERVAL_MS);

    try {
      await api.runTicket(id);
      await Promise.all([refreshTickets(), refreshApprovals(), loadHistory(id)]);
    } catch (err) {
      setLiveError(err instanceof ApiRequestError ? err.message : "The agent run failed unexpectedly.");
    } finally {
      if (pollHandle.current !== null) {
        window.clearInterval(pollHandle.current);
        pollHandle.current = null;
      }
      setIsLive(false);
      setRunningId(null);
      setLiveEvents([]);
    }
  }

  async function handleApprove(approvalId: string, approverName: string) {
    setApprovingId(approvalId);
    setApproveError(null);
    try {
      await api.approvePayment(approvalId, approverName);
      setCashPulse(true);
      window.setTimeout(() => setCashPulse(false), 1200);
      await Promise.all([refreshCash(), refreshApprovals(), refreshTickets()]);
      if (selectedId !== null) await loadHistory(selectedId);
    } catch (err) {
      setApproveError(err instanceof ApiRequestError ? err.message : "Approval failed unexpectedly.");
    } finally {
      setApprovingId(null);
    }
  }

  useEffect(() => {
    return () => {
      if (pollHandle.current !== null) window.clearInterval(pollHandle.current);
    };
  }, []);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__brand">
          <span className="app-header__crest">CC</span>
          <div>
            <h1>Campus Customs — AI Operations Desk</h1>
            <p className="app-header__subtitle">Live agent coordination for the campus shop</p>
          </div>
        </div>
        <div className={`status-indicator ${backendUp ? "status-indicator--ok" : "status-indicator--down"}`}>
          <span className="status-dot" />
          {backendUp ? "Backend connected" : "Backend unreachable"}
        </div>
      </header>

      <main className="app-grid">
        <TicketQueue
          tickets={tickets}
          loading={ticketsLoading}
          error={ticketsError}
          selectedId={selectedId}
          runningId={runningId}
          onSelect={handleSelect}
          onRun={handleRun}
        />

        <AgentTimeline
          ticket={selectedTicket}
          isLive={isLive}
          liveEvents={liveEvents}
          liveError={liveError}
          runGroups={runGroups}
          selectedRunId={selectedRunId}
          onSelectRun={setSelectedRunId}
          systemEvents={systemEvts}
        />
        {historyLoadError && <p className="error-text" style={{ gridColumn: "2" }}>{historyLoadError}</p>}

        <div className="right-column">
          <AgentRoster />
          <CashPanel cash={cash} loading={cashLoading} error={cashError} justChanged={cashPulse} />
          <ApprovalsPanel
            approvals={approvals}
            loading={approvalsLoading}
            error={approvalsError}
            onApprove={handleApprove}
            approvingId={approvingId}
            approveError={approveError}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
