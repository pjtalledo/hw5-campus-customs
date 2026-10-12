import type { AgentRole } from "./types";

export interface AgentMeta {
  label: string;
  short: string;
  color: string;
  description: string;
}

export const AGENT_META: Record<AgentRole, AgentMeta> = {
  boss: {
    label: "Boss",
    short: "B",
    color: "#00356B", // Yale Blue
    description: "Coordinates the team, delegates, and makes the final call.",
  },
  inventory: {
    label: "Inventory",
    short: "I",
    color: "#2E7D32",
    description: "Stock, restocking, and vendor constraints.",
  },
  accounting: {
    label: "Accounting",
    short: "A",
    color: "#C7B14E", // restrained gold accent
    description: "Cash, invoices, and payment safety.",
  },
  facilities: {
    label: "Facilities",
    short: "F",
    color: "#6A4C93",
    description: "Lease, rent, and facility obligations.",
  },
  customer_service: {
    label: "Customer Service",
    short: "CS",
    color: "#B3541E",
    description: "Customer requests, pricing, and drafted responses.",
  },
  system: {
    label: "System",
    short: "S",
    color: "#5A6472",
    description: "Backend-initiated actions (e.g. a human approval or reset).",
  },
};
