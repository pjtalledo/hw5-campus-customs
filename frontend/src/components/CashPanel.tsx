import type { CashAccount } from "../types";

interface Props {
  cash: CashAccount | null;
  loading: boolean;
  error: string | null;
  justChanged: boolean;
}

export function CashPanel({ cash, loading, error, justChanged }: Props) {
  return (
    <section className="panel cash-panel" aria-label="Checking balance">
      <h2 className="panel-title">Checking Balance</h2>
      {loading && <p className="muted">Loading…</p>}
      {error && <p className="error-text">{error}</p>}
      {cash && (
        <div className={`cash-amount ${justChanged ? "cash-amount--pulse" : ""}`}>
          <span className="cash-currency">$</span>
          {cash.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          <div className="cash-meta">
            {cash.name} · as of {cash.date}
          </div>
        </div>
      )}
    </section>
  );
}
