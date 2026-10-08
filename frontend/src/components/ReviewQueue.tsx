import { useEffect, useState } from "react";
import {
  listReviewTasks,
  statusLabels,
  type ReviewPage,
  type ReviewStatus,
} from "../review-api";
import ReviewTaskDetail from "./ReviewTaskDetail";

const buttonClass =
  "rounded-lg bg-freight-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50";
export default function ReviewQueue() {
  const [status, setStatus] = useState<ReviewStatus | "">("pending");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ReviewPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    void listReviewTasks(status, page, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setData(result);
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted)
          setError(
            err instanceof Error ? err.message : "Failed to load review queue",
          );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [status, page, revision]);

  if (selected !== null)
    return (
      <ReviewTaskDetail
        key={selected}
        id={selected}
        onBack={() => {
          setSelected(null);
          setRevision((value) => value + 1);
        }}
      />
    );

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold">Document Review</h1>
          <p className="mt-2 text-slate-600">
            Follow up on audit exceptions and record how they were resolved.
          </p>
        </div>
        <button
          className={buttonClass}
          onClick={() => setRevision((value) => value + 1)}
          disabled={loading}
        >
          Refresh queue
        </button>
      </div>
      <label className="block text-sm font-medium">
        Filter by status
        <select
          className="ml-3 rounded-lg border border-slate-300 bg-white p-2"
          value={status}
          onChange={(event) => {
            setStatus(event.target.value as ReviewStatus | "");
            setPage(1);
          }}
        >
          <option value="">All statuses</option>
          {Object.entries(statusLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {loading ? (
        <p role="status">Loading review tasks…</p>
      ) : error ? (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800"
        >
          {error}
        </div>
      ) : (
        data && (
          <>
            <p className="text-sm text-slate-500">
              {data.total} tasks · Page {page}
            </p>
            {data.items.length === 0 ? (
              <p className="rounded-xl border border-slate-200 bg-white p-8 text-slate-600">
                No review tasks match this filter. New audit exceptions appear
                automatically; refresh to check again.
              </p>
            ) : (
              <ul className="space-y-3">
                {data.items.map((task) => (
                  <li key={task.id}>
                    <button
                      className="w-full rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm hover:border-freight-500"
                      onClick={() => setSelected(task.id)}
                    >
                      <span className="flex flex-wrap justify-between gap-2">
                        <strong className="text-freight-700">
                          {task.original_filename}
                        </strong>
                        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs">
                          {statusLabels[task.status]}
                        </span>
                      </span>
                      <span className="mt-2 block text-sm text-slate-600">
                        {task.invoice_number ?? `Document #${task.document_id}`}{" "}
                        · {task.carrier_name ?? "Carrier unavailable"}
                      </span>
                      <span className="mt-2 block text-sm">{task.reason}</span>
                      <span className="mt-2 block text-xs text-slate-500">
                        Created {new Date(task.created_at).toLocaleString()}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex gap-3">
              <button
                className={buttonClass}
                disabled={page <= 1}
                onClick={() => setPage((value) => value - 1)}
              >
                Previous
              </button>
              <button
                className={buttonClass}
                disabled={page * data.page_size >= data.total}
                onClick={() => setPage((value) => value + 1)}
              >
                Next
              </button>
            </div>
          </>
        )
      )}
    </section>
  );
}
