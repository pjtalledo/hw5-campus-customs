// Typed client for the real Problem 7 FastAPI backend. No mock data, no
// hardcoded results -- every function here makes a real fetch() to
// http://localhost:8000 and returns the backend's actual response.

import type {
  ApprovalsResponse,
  ApprovePaymentResult,
  CashAccount,
  EventsResponse,
  RunTicketResponse,
  Ticket,
} from "./types";

const BASE_URL = "http://localhost:8000";

class ApiRequestError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiRequestError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiRequestError(0, "Could not reach the backend at http://localhost:8000. Is it running?");
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      // response had no JSON body; keep the generic message
    }
    throw new ApiRequestError(response.status, detail);
  }
  return (await response.json()) as T;
}

export { ApiRequestError };

export async function getTickets(): Promise<Ticket[]> {
  const data = await request<{ tickets: Ticket[] }>("/tickets");
  return data.tickets;
}

export async function runTicket(ticketId: number): Promise<RunTicketResponse> {
  return request<RunTicketResponse>(`/tickets/${ticketId}/run`, { method: "POST" });
}

export async function getEvents(opts: {
  ticketId?: number;
  runId?: string;
  limit?: number;
} = {}): Promise<EventsResponse> {
  const params = new URLSearchParams();
  if (opts.ticketId !== undefined) params.set("ticket_id", String(opts.ticketId));
  if (opts.runId !== undefined) params.set("run_id", opts.runId);
  params.set("limit", String(opts.limit ?? 100));
  return request<EventsResponse>(`/events?${params.toString()}`);
}

export async function getCash(account = "checking"): Promise<CashAccount> {
  return request<CashAccount>(`/cash?account=${encodeURIComponent(account)}`);
}

export async function getApprovals(status = "pending"): Promise<ApprovalsResponse> {
  return request<ApprovalsResponse>(`/approvals?status=${encodeURIComponent(status)}`);
}

export async function approvePayment(
  approvalId: string,
  approverName: string,
): Promise<ApprovePaymentResult> {
  return request<ApprovePaymentResult>(`/payments/${encodeURIComponent(approvalId)}/approve`, {
    method: "POST",
    body: JSON.stringify({ approval_id: approvalId, approver_name: approverName }),
  });
}
