import { useState } from "react";
import type { PendingApproval } from "../types";

interface Props {
  approvals: PendingApproval[];
  loading: boolean;
  error: string | null;
  onApprove: (approvalId: string, approverName: string) => Promise<void>;
  approvingId: string | null;
  approveError: string | null;
}

export function ApprovalsPanel({ approvals, loading, error, onApprove, approvingId, approveError }: Props) {
  const [name, setName] = useState("");

  return (
    <section className="panel approvals-panel" aria-label="Pending human approvals">
      <h2 className="panel-title">Pending Approvals</h2>
      <p className="muted small">
        A click alone is not authentication. Enter your name to confirm you are the human authorizing this
        exact payment.
      </p>

      {loading && <p className="muted">Loading…</p>}
      {error && <p className="error-text">{error}</p>}
      {!loading && !error && approvals.length === 0 && (
        <p className="muted">No pending approvals right now.</p>
      )}

      <input
        className="approver-input"
        type="text"
        placeholder="Your name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        aria-label="Approver name"
      />

      <ul className="approval-list">
        {approvals.map((a) => (
          <li key={a.approval_id} className="approval-card">
            <div className="approval-card__row">
              <span className="approval-card__kind">{a.kind}</span>
              <span className="approval-card__amount">
                ${a.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
            </div>
            <div className="approval-card__detail">
              {a.kind === "invoice" ? `Invoice #${a.ref_id}` : `Lease #${a.ref_id}`} · from {a.account}
            </div>
            <div className="approval-card__reason">{a.reason}</div>
            <div className="approval-card__requested">Requested by: {a.requested_by}</div>
            <button
              className="btn btn--gold btn--block"
              disabled={!name.trim() || approvingId === a.approval_id}
              onClick={() => onApprove(a.approval_id, name.trim())}
            >
              {approvingId === a.approval_id ? "Approving…" : "Approve payment"}
            </button>
          </li>
        ))}
      </ul>
      {approveError && <p className="error-text">{approveError}</p>}
    </section>
  );
}
