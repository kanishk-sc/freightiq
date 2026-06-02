import type { Invoice, LineItem } from "../api";

interface InvoiceTableProps {
  invoice: Invoice;
}

function formatMoney(value: number | null): string {
  if (value === null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

function formatCell(value: string | null): string {
  return value ?? "—";
}

export default function InvoiceTable({ invoice }: InvoiceTableProps) {
  const fields: { label: string; value: string }[] = [
    { label: "Carrier", value: formatCell(invoice.carrier_name) },
    { label: "Invoice #", value: formatCell(invoice.invoice_number) },
    { label: "Invoice Date", value: formatCell(invoice.invoice_date) },
    { label: "Due Date", value: formatCell(invoice.due_date) },
    { label: "Load ID", value: formatCell(invoice.load_id) },
    { label: "Origin", value: formatCell(invoice.origin) },
    { label: "Destination", value: formatCell(invoice.destination) },
    { label: "Subtotal", value: formatMoney(invoice.subtotal) },
    { label: "Taxes", value: formatMoney(invoice.taxes) },
    { label: "Total", value: formatMoney(invoice.total_amount) },
  ];

  return (
    <div className="space-y-8">
      <section>
        <h2 className="font-display mb-4 text-lg font-semibold text-slate-800">
          Invoice Details
        </h2>
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <tbody>
              {fields.map((row) => (
                <tr key={row.label} className="border-b border-slate-100 last:border-0">
                  <th className="w-40 bg-slate-50 px-4 py-3 text-left font-medium text-slate-600">
                    {row.label}
                  </th>
                  <td className="px-4 py-3 text-slate-900">{row.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="font-display mb-4 text-lg font-semibold text-slate-800">
          Line Items
        </h2>
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-slate-600">
                <th className="px-4 py-3 font-medium">Description</th>
                <th className="px-4 py-3 font-medium text-right">Qty</th>
                <th className="px-4 py-3 font-medium text-right">Unit Price</th>
                <th className="px-4 py-3 font-medium text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {invoice.line_items.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                    No line items extracted
                  </td>
                </tr>
              ) : (
                invoice.line_items.map((item: LineItem, idx: number) => (
                  <tr
                    key={item.id ?? idx}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="px-4 py-3">{formatCell(item.description)}</td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {item.quantity ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {formatMoney(item.unit_price)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums font-medium">
                      {formatMoney(item.total)}
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
