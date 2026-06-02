import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  getInvoice,
  runAudit,
  uploadInvoice,
  type AuditFlag,
  type FlagCounts,
  type Invoice,
} from "./api";
import AuditPanel from "./components/AuditPanel";
import Dashboard from "./components/Dashboard";
import InvoiceTable from "./components/InvoiceTable";
import UploadZone from "./components/UploadZone";

type View = "upload" | "detail" | "dashboard";

export default function App() {
  const [view, setView] = useState<View>("upload");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [auditFlags, setAuditFlags] = useState<AuditFlag[]>([]);
  const [flagCounts, setFlagCounts] = useState<FlagCounts>({
    errors: 0,
    warnings: 0,
    total: 0,
  });

  const loadInvoice = useCallback(async (id: number) => {
    setDetailLoading(true);
    setUploadError(null);
    try {
      const data = await getInvoice(id);
      setInvoice(data);
      setAuditFlags(data.audit_flags);
      setFlagCounts(data.flag_counts);
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Failed to load invoice");
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (view === "detail" && selectedId !== null) {
      void loadInvoice(selectedId);
    }
  }, [view, selectedId, loadInvoice]);

  const handleUpload = async (file: File) => {
    setUploadLoading(true);
    setUploadError(null);
    try {
      const data = await uploadInvoice(file);
      setSelectedId(data.id);
      setInvoice(data);
      setAuditFlags(data.audit_flags);
      setFlagCounts(data.flag_counts);
      setView("detail");
    } catch (err) {
      setUploadError(
        err instanceof ApiError ? err.message : "Upload failed. Please try again."
      );
    } finally {
      setUploadLoading(false);
    }
  };

  const handleAudit = async () => {
    if (!selectedId) return;
    setAuditLoading(true);
    setAuditError(null);
    try {
      const result = await runAudit(selectedId);
      setAuditFlags(result.audit_flags);
      setFlagCounts(result.flag_counts);
      await loadInvoice(selectedId);
    } catch (err) {
      setAuditError(err instanceof ApiError ? err.message : "Audit failed. Please try again.");
    } finally {
      setAuditLoading(false);
    }
  };

  const goToDetail = (id: number) => {
    setSelectedId(id);
    setView("detail");
  };

  const navLinkClass = (active: boolean) =>
    `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
      active
        ? "bg-freight-600 text-white"
        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
    }`;

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <button
            type="button"
            onClick={() => {
              setView("upload");
              setUploadError(null);
            }}
            className="flex items-center gap-2 text-left"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-freight-600 text-sm font-bold text-white">
              FQ
            </div>
            <div>
              <span className="font-display text-xl font-bold text-slate-900">FreightIQ</span>
              <p className="text-xs text-slate-500">AI Freight Invoice Auditor</p>
            </div>
          </button>
          <nav className="flex gap-1">
            <button
              type="button"
              className={navLinkClass(view === "upload")}
              onClick={() => {
                setView("upload");
                setUploadError(null);
              }}
            >
              Upload
            </button>
            <button
              type="button"
              className={navLinkClass(view === "dashboard")}
              onClick={() => setView("dashboard")}
            >
              Dashboard
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        {view === "upload" && (
          <div>
            <div className="mb-8 text-center">
              <h1 className="font-display text-2xl font-bold text-slate-900 sm:text-3xl">
                Upload Freight Invoice
              </h1>
              <p className="mt-2 text-slate-600">
                Drop a PDF to extract fields and run an AI-powered billing audit.
              </p>
            </div>
            <UploadZone onUpload={handleUpload} loading={uploadLoading} error={uploadError} />
          </div>
        )}

        {view === "dashboard" && <Dashboard onSelectInvoice={goToDetail} />}

        {view === "detail" && (
          <div className="space-y-8">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <button
                  type="button"
                  onClick={() => setView("upload")}
                  className="mb-2 text-sm text-freight-600 hover:underline"
                >
                  ← Upload another
                </button>
                <h1 className="font-display text-2xl font-bold text-slate-900">
                  {invoice?.invoice_number
                    ? `Invoice ${invoice.invoice_number}`
                    : "Invoice Detail"}
                </h1>
              </div>
              <button
                type="button"
                onClick={() => void handleAudit()}
                disabled={auditLoading || detailLoading || !selectedId}
                className="rounded-lg bg-freight-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-freight-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {auditLoading ? "Auditing…" : "Run Audit"}
              </button>
            </div>

            {detailLoading && !invoice ? (
              <div className="flex justify-center py-16">
                <div className="h-10 w-10 animate-spin rounded-full border-4 border-freight-100 border-t-freight-600" />
              </div>
            ) : invoice ? (
              <>
                <InvoiceTable invoice={invoice} />
                <AuditPanel
                  flags={auditFlags}
                  flagCounts={flagCounts}
                  loading={auditLoading}
                  error={auditError}
                />
              </>
            ) : (
              uploadError && (
                <div role="alert" className="text-red-700">
                  {uploadError}
                </div>
              )
            )}
          </div>
        )}
      </main>
    </div>
  );
}
