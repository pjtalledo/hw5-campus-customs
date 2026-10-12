// Groups a ticket's raw, flat event history (as returned by GET /events) into
// genuine agent runs, keyed by the real run_id every event already carries.
// No field is invented here -- this only reorganizes real backend data.

import type { AgentRole, AuditEvent } from "./types";

export interface RunGroup {
  runId: string;
  events: AuditEvent[];
  startedAt: string;
  endedAt: string;
  /** Extracted from the real boss agent_end event's detail.output, if present
   * in this run -- the same data desk_tickets.html's Actual sections use. */
  finalSummary: { summary: string; recommendation: string; requires_human_approval: boolean } | null;
}

/** System-initiated events (ticket closure, recorded approvals, resets) are
 * never part of an agent run -- they have no genuine run association and
 * must not be folded into the run selector as if they were. */
export function isSystemEvent(e: AuditEvent): boolean {
  return (e.agent as AgentRole) === "system";
}

export function groupEventsByRun(events: AuditEvent[]): RunGroup[] {
  const byRun = new Map<string, AuditEvent[]>();
  for (const e of events) {
    if (isSystemEvent(e)) continue;
    const list = byRun.get(e.run_id) ?? [];
    list.push(e);
    byRun.set(e.run_id, list);
  }

  const groups: RunGroup[] = [];
  for (const [runId, evts] of byRun) {
    const sorted = [...evts].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
    const bossEnd = sorted.find(
      (e) => e.agent === "boss" && e.event_type === "agent_end" && e.detail && "output" in e.detail
    );
    const output = bossEnd?.detail.output as
      | { summary?: string; recommendation?: string; requires_human_approval?: boolean }
      | undefined;
    groups.push({
      runId,
      events: sorted,
      startedAt: sorted[0].timestamp,
      endedAt: sorted[sorted.length - 1].timestamp,
      finalSummary: output
        ? {
            summary: output.summary ?? "",
            recommendation: output.recommendation ?? "",
            requires_human_approval: output.requires_human_approval ?? false,
          }
        : null,
    });
  }

  groups.sort((a, b) => b.startedAt.localeCompare(a.startedAt));
  return groups;
}

export function extractSystemEvents(events: AuditEvent[]): AuditEvent[] {
  return events.filter(isSystemEvent).sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}
