// Types mirror the actual backend/main.py response shapes exactly
// (backend/models.py). Nothing here is invented -- every field matches a
// real field the FastAPI backend actually returns.

export type AgentRole =
  | "boss"
  | "inventory"
  | "accounting"
  | "facilities"
  | "customer_service"
  | "system";

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  status: string; // "open" | "resolved" (whatever the DB actually says)
  notes: string | null;
  created_at: string;
}

export interface DelegationRecord {
  from_agent: AgentRole;
  to_agent: AgentRole;
  reason: string;
  depth: number;
}

export interface TicketResolution {
  ticket_id: number;
  summary: string;
  recommendation: string;
  requires_human_approval: boolean;
  delegations: DelegationRecord[];
  run_id: string;
}

export interface RunTicketResponse {
  run_id: string;
  result: TicketResolution;
}

export type AuditEventType =
  | "agent_start"
  | "agent_end"
  | "delegation"
  | "mcp_tool_call"
  | "approval_request"
  | "approval_recorded"
  | "reset"
  | "error";

export interface AuditEvent {
  timestamp: string;
  run_id: string;
  ticket_id: number | null;
  agent: AgentRole;
  event_type: AuditEventType;
  detail: Record<string, unknown>;
}

export interface EventsResponse {
  events: AuditEvent[];
  count: number;
  total_matching: number;
}

export interface CashAccount {
  name: string;
  balance: number;
  date: string;
}

export interface PendingApproval {
  approval_id: string;
  kind: string;
  ref_id: number;
  amount: number;
  account: string;
  reason: string;
  requested_by: string;
  status: "pending" | "approved" | "consumed" | "rejected";
  created_at: string;
  approved_by: string | null;
  approved_at: string | null;
  consumed_at: string | null;
}

export interface ApprovalsResponse {
  approvals: PendingApproval[];
}

export interface ApprovePaymentResult {
  payment?: {
    id: number;
    kind: string;
    ref_id: number;
    amount: number;
    account: string;
    paid_at: string;
    approved_by: string;
  };
  new_account_balance?: number;
  approval_id?: string;
}

export interface ApiError {
  detail: string;
}
