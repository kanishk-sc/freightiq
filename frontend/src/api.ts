const API_BASE = "/api";

export interface LineItem {
  id?: number;
  description: string | null;
  quantity: number | null;
  unit_price: number | null;
  total: number | null;
}

export interface AuditFlag {
  id?: number;
  field: string;
  severity: "warning" | "error";
  description: string;
}

export interface FlagCounts {
  errors: number;
  warnings: number;
  total: number;
}

export interface Invoice {
  id: number;
  carrier_name: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  due_date: string | null;
  origin: string | null;
  destination: string | null;
  load_id: string | null;
  subtotal: number | null;
  taxes: number | null;
  total_amount: number | null;
  audited: boolean;
  created_at: string | null;
  line_items: LineItem[];
  audit_flags: AuditFlag[];
  flag_counts: FlagCounts;
}

export interface InvoiceSummary {
  id: number;
  carrier_name: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  total_amount: number | null;
  audited: boolean;
  flag_counts: FlagCounts;
}

export interface AuditResponse {
  invoice_id: number;
  audit_flags: AuditFlag[];
  flag_counts: FlagCounts;
}

export interface DashboardStats {
  total_invoices: number;
  total_audited: number;
  total_errors: number;
  total_warnings: number;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* use statusText */
    }
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

export async function uploadInvoice(file: File): Promise<Invoice> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<Invoice>(response);
}

export async function runAudit(invoiceId: number): Promise<AuditResponse> {
  const response = await fetch(`${API_BASE}/audit/${invoiceId}`, {
    method: "POST",
  });
  return handleResponse<AuditResponse>(response);
}

export async function listInvoices(): Promise<InvoiceSummary[]> {
  const response = await fetch(`${API_BASE}/invoices`);
  return handleResponse<InvoiceSummary[]>(response);
}

export async function getInvoice(invoiceId: number): Promise<Invoice> {
  const response = await fetch(`${API_BASE}/invoices/${invoiceId}`);
  return handleResponse<Invoice>(response);
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const response = await fetch(`${API_BASE}/dashboard`);
  return handleResponse<DashboardStats>(response);
}
