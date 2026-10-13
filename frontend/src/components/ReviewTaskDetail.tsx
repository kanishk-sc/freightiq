import { useEffect, useState } from "react";
import { getInvoice, type Invoice } from "../api";
import {
  getReviewHistory,
  getReviewTask,
  statusLabels,
  updateReviewTask,
  type ReviewDetail,
  type ReviewHistory,
  type ReviewStatus,
} from "../review-api";
import AuditPanel from "./AuditPanel";
import InvoiceTable from "./InvoiceTable";

export default function ReviewTaskDetail({
  id,
  onBack,
}: {
  id: number;
  onBack: () => void;
}) {
  const [task, setTask] = useState<ReviewDetail | null>(null);
  const [history, setHistory] = useState<ReviewHistory[]>([]);
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [notes, setNotes] = useState("");
  const [resolution, setResolution] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [invoiceError, setInvoiceError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setInvoice(null);
    setInvoiceError(null);
    void Promise.all([
      getReviewTask(id, controller.signal),
      getReviewHistory(id, controller.signal),
    ])
      .then(async ([detail, events]) => {
        if (!active) return;
        setTask(detail);
        setHistory(events);
        setNotes(detail.notes);
        setResolution(detail.resolution);
        if (detail.invoice_id !== null) {
          try {
            const record = await getInvoice(detail.invoice_id);
            if (active) setInvoice(record);
          } catch {
            if (active)
              setInvoiceError(
                "Invoice information could not be loaded. Reload to try again.",
              );
          }
        }
      })
      .catch((err: unknown) => {
        if (active)
          setError(err instanceof Error ? err.message : "Failed to load task");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [id, revision]);

  const save = async (status?: ReviewStatus) => {
    if (!task) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateReviewTask(id, {
        version: task.version,
        notes,
        resolution,
        ...(status ? { status } : {}),
      });
      setTask({ ...task, ...updated });
      setNotes(updated.notes);
      setResolution(updated.resolution);
      setSuccess("Review task saved.");
      try {
        setHistory(await getReviewHistory(id));
      } catch {
        setError(
          "Task saved, but history could not be refreshed. Reload to view it.",
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save task");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="space-y-6">
      <div className="flex gap-4">
        <button
          className="text-sm text-freight-700 hover:underline"
          disabled={saving}
          onClick={onBack}
        >
          ← Back to review queue
        </button>
        <button
          className="text-sm text-freight-700 hover:underline"
          disabled={saving || loading}
          onClick={() => {
            setSuccess(null);
            setRevision((value) => value + 1);
          }}
        >
          Reload task
        </button>
      </div>
      {loading ? (
        <p role="status">Loading task…</p>
      ) : (
        <>
          {error && (
            <p role="alert" className="rounded-lg bg-red-50 p-4 text-red-800">
              {error}
            </p>
          )}
          {success && (
            <p
              role="status"
              className="rounded-lg bg-emerald-50 p-4 text-emerald-800"
            >
              {success}
            </p>
          )}
          {task && (
            <>
              <div>
                <h1 className="font-display text-2xl font-bold">
                  {task.original_filename}
                </h1>
                <p className="mt-2 font-medium">
                  {statusLabels[task.status]} · Document #{task.document_id}
                </p>
                <p className="mt-2 text-slate-600">{task.reason}</p>
                <p className="mt-2 text-xs text-slate-500">
                  Updated {new Date(task.updated_at).toLocaleString()}
                </p>
              </div>
              <form
                className="space-y-4 rounded-xl border border-slate-200 bg-white p-5"
                onSubmit={(event) => {
                  event.preventDefault();
                  void save();
                }}
              >
                <label className="block text-sm font-medium">
                  Review notes
                  <textarea
                    className="mt-2 block w-full rounded-lg border border-slate-300 p-3"
                    rows={3}
                    value={notes}
                    maxLength={10000}
                    disabled={saving}
                    onChange={(event) => setNotes(event.target.value)}
                  />
                </label>
                <label className="block text-sm font-medium">
                  Resolution notes
                  <textarea
                    className="mt-2 block w-full rounded-lg border border-slate-300 p-3"
                    rows={3}
                    value={resolution}
                    maxLength={10000}
                    disabled={saving}
                    onChange={(event) => setResolution(event.target.value)}
                  />
                </label>
                <p className="text-xs text-slate-500">
                  Resolution notes are required to resolve a task. This records
                  your decision; extracted invoice values remain as observed.
                </p>
                <div className="flex flex-wrap gap-3">
                  <button
                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm disabled:opacity-50"
                    disabled={saving}
                    type="submit"
                  >
                    {saving ? "Saving…" : "Save notes"}
                  </button>
                  {task.status !== "resolved" && (
                    <button
                      type="button"
                      className="rounded-lg bg-freight-600 px-4 py-2 text-sm text-white disabled:opacity-50"
                      disabled={
                        saving ||
                        (task.status === "in_review" && !resolution.trim())
                      }
                      onClick={() =>
                        void save(
                          task.status === "pending" ? "in_review" : "resolved",
                        )
                      }
                    >
                      {task.status === "pending"
                        ? "Start review"
                        : "Resolve task"}
                    </button>
                  )}
                </div>
              </form>
              <section>
                <h2 className="mb-3 font-display text-lg font-semibold">
                  Review history
                </h2>
                <ol className="space-y-3">
                  {history.map((event) => (
                    <li
                      key={event.id}
                      className="rounded-lg border border-slate-200 bg-white p-4 text-sm"
                    >
                      <p className="font-medium">
                        {event.from_status === null
                          ? "Created"
                          : statusLabels[event.from_status]}{" "}
                        → {statusLabels[event.to_status]}
                      </p>
                      <p className="text-xs text-slate-500">
                        {new Date(event.created_at).toLocaleString()} ·{" "}
                        {event.origin} · Version {event.version}
                      </p>
                      {event.notes && (
                        <p className="mt-2 whitespace-pre-wrap">
                          Notes: {event.notes}
                        </p>
                      )}
                      {event.resolution && (
                        <p className="mt-2 whitespace-pre-wrap">
                          Resolution: {event.resolution}
                        </p>
                      )}
                    </li>
                  ))}
                </ol>
              </section>
              {invoiceError ? (
                <p role="alert" className="text-red-800">
                  {invoiceError}
                </p>
              ) : invoice ? (
                <>
                  <InvoiceTable invoice={invoice} />
                  <AuditPanel
                    flags={invoice.audit_flags}
                    flagCounts={invoice.flag_counts}
                  />
                </>
              ) : (
                <p className="text-slate-600">
                  No extracted invoice is available. Processing outcome:{" "}
                  {task.error_code ?? "not yet processed"}.
                </p>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}
