import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  getDashboardStats,
  listInvoices,
  type DashboardStats,
  type InvoiceSummary,
} from "../api";

interface DashboardProps {
  onSelectInvoice: (id: number) => void;
}

function formatMoney(value: number | null): string {
  if (value === null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

function statusLabel(inv: InvoiceSummary): string {
  if (!inv.audited) return "Pending audit";
  if (inv.flag_counts.errors > 0) return "Issues found";
  if (inv.flag_counts.warnings > 0) return "Review suggested";
  return "Clean";
}

export default function Dashboard({ onSelectInvoice }: DashboardProps) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [invoices, setInvoices] = useState<InvoiceSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, list] = await Promise.all([getDashboardStats(), listInvoices()]);
      setStats(s);
      setInvoices(list);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-freight-100 border-t-freight-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-800">
        {error}
      </div>
    );
  }

  const cards = stats
    ? [
        { label: "Invoices Uploaded", value: stats.total_invoices },
        { label: "Audited", value: stats.total_audited },
        { label: "Errors Found", value: stats.total_errors, accent: "text-red-600" },
        { label: "Warnings", value: stats.total_warnings, accent: "text-amber-600" },
      ]
    : [];

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <p className="text-sm font-medium text-slate-500">{card.label}</p>
            <p
              className={`font-display mt-2 text-3xl font-bold ${card.accent ?? "text-slate-900"}`}
            >
              {card.value}
            </p>
          </div>
        ))}
      </div>

      <section>
        <h2 className="font-display mb-4 text-lg font-semibold text-slate-800">
          Recent Invoices
        </h2>
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-slate-600">
                <th className="px-4 py-3 font-medium">Invoice #</th>
                <th className="px-4 py-3 font-medium">Carrier</th>
                <th className="px-4 py-3 font-medium">Date</th>
                <th className="px-4 py-3 font-medium text-right">Amount</th>
                <th className="px-4 py-3 font-medium text-center">Flags</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {invoices.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                    No invoices yet. Upload a PDF to get started.
                  </td>
                </tr>
              ) : (
                invoices.map((inv) => (
                  <tr
                    key={inv.id}
                    className="cursor-pointer border-b border-slate-100 transition-colors hover:bg-freight-50/50 last:border-0"
                    onClick={() => onSelectInvoice(inv.id)}
                  >
                    <td className="px-4 py-3 font-medium text-freight-700">
                      {inv.invoice_number ?? `#${inv.id}`}
                    </td>
                    <td className="px-4 py-3">{inv.carrier_name ?? "—"}</td>
                    <td className="px-4 py-3">{inv.invoice_date ?? "—"}</td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {formatMoney(inv.total_amount)}
                    </td>
                    <td className="px-4 py-3 text-center tabular-nums">
                      {inv.flag_counts.total}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          !inv.audited
                            ? "bg-slate-100 text-slate-700"
                            : inv.flag_counts.errors > 0
                              ? "bg-red-100 text-red-800"
                              : inv.flag_counts.warnings > 0
                                ? "bg-amber-100 text-amber-800"
                                : "bg-emerald-100 text-emerald-800"
                        }`}
                      >
                        {statusLabel(inv)}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
