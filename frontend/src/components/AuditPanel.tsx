import type { AuditFlag, FlagCounts } from "../api";

interface AuditPanelProps {
  flags: AuditFlag[];
  flagCounts: FlagCounts;
  loading?: boolean;
  error?: string | null;
}

function SeverityBadge({ severity }: { severity: "warning" | "error" }) {
  if (severity === "error") {
    return (
      <span className="inline-flex rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-800">
        Error
      </span>
    );
  }
  return (
    <span className="inline-flex rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800">
      Warning
    </span>
  );
}

export default function AuditPanel({
  flags,
  flagCounts,
  loading,
  error,
}: AuditPanelProps) {
  if (loading) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-6">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-freight-100 border-t-freight-600" />
        <p className="text-slate-700">Running AI audit…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
      >
        {error}
      </div>
    );
  }

  if (flags.length === 0 && flagCounts.total === 0) {
    return null;
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-slate-800 px-5 py-4 text-white">
        <h2 className="font-display text-lg font-semibold">Audit Results</h2>
        <div className="flex gap-4 text-sm">
          <span>
            <strong className="text-red-300">{flagCounts.errors}</strong> errors
          </span>
          <span className="text-slate-400">|</span>
          <span>
            <strong className="text-amber-300">{flagCounts.warnings}</strong> warnings
          </span>
        </div>
      </div>

      <ul className="space-y-3">
        {flags.map((flag, idx) => (
          <li
            key={flag.id ?? idx}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {flag.field}
                </p>
                <p className="mt-1 text-slate-800">{flag.description}</p>
              </div>
              <SeverityBadge severity={flag.severity} />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
