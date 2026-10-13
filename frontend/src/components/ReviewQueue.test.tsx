import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ReviewDetail, ReviewHistory } from "../review-api";
import ReviewQueue from "./ReviewQueue";

const initial: ReviewDetail = {
  id: 7,
  document_id: 3,
  status: "pending",
  reason: "Required invoice number is missing",
  notes: "",
  resolution: "",
  version: 1,
  original_filename: "carrier-invoice.pdf",
  invoice_id: null,
  invoice_number: null,
  carrier_name: "North Freight",
  error_code: "pdf_has_no_text",
  created_at: "2026-10-08T10:00:00Z",
  updated_at: "2026-10-08T10:00:00Z",
  in_review_at: null,
  resolved_at: null,
};

function installApi() {
  let stored = { ...initial };
  const history: ReviewHistory[] = [
    {
      id: 1,
      task_id: 7,
      from_status: null,
      to_status: "pending",
      notes: "",
      resolution: "",
      version: 1,
      origin: "pipeline",
      created_at: initial.created_at,
    },
  ];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, options?: RequestInit) => {
      if (options?.method === "PATCH") {
        const change = JSON.parse(
          options.body as string,
        ) as Partial<ReviewDetail>;
        if (change.version !== stored.version)
          return new Response(
            JSON.stringify({
              error: { message: "Task changed; reload before saving" },
            }),
            { status: 409 },
          );
        const from = stored.status;
        stored = { ...stored, ...change, version: stored.version + 1 };
        history.push({
          id: history.length + 1,
          task_id: 7,
          from_status: from,
          to_status: stored.status,
          notes: stored.notes,
          resolution: stored.resolution,
          version: stored.version,
          origin: "operator",
          created_at: initial.created_at,
        });
        return Response.json(stored);
      }
      if (input.endsWith("/history")) return Response.json(history);
      if (input.endsWith("/7")) return Response.json(stored);
      const status = new URL(input, "http://localhost").searchParams.get(
        "status",
      );
      return Response.json({
        items: !status || status === stored.status ? [stored] : [],
        total: !status || status === stored.status ? 1 : 0,
        page: 1,
        page_size: 20,
      });
    }),
  );
}

describe("document review workflow", () => {
  it("renders the queue, filters and displays an empty result", async () => {
    installApi();
    render(<ReviewQueue />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading review tasks",
    );
    expect(
      await screen.findByRole("button", { name: /carrier-invoice.pdf/ }),
    ).toBeInTheDocument();
    await userEvent.selectOptions(
      screen.getByLabelText("Filter by status"),
      "resolved",
    );
    expect(
      await screen.findByText(/No review tasks match/),
    ).toBeInTheDocument();
  });
  it("shows API errors and retries successfully", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json(
          { error: { message: "Review service is temporarily unavailable" } },
          { status: 503 },
        ),
      ),
    );
    render(<ReviewQueue />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "temporarily unavailable",
    );
    installApi();
    await userEvent.click(
      screen.getByRole("button", { name: "Refresh queue" }),
    );
    expect(
      await screen.findByRole("button", { name: /carrier-invoice.pdf/ }),
    ).toBeInTheDocument();
  });
  it("persists notes and valid status changes through the typed HTTP client", async () => {
    installApi();
    render(<ReviewQueue />);
    await userEvent.click(
      await screen.findByRole("button", { name: /carrier-invoice.pdf/ }),
    );
    await screen.findByRole("button", { name: "Start review" });
    await userEvent.type(
      screen.getByLabelText("Review notes"),
      "Carrier contacted",
    );
    await userEvent.click(screen.getByRole("button", { name: "Start review" }));
    const resolve = await screen.findByRole("button", { name: "Resolve task" });
    expect(resolve).toBeDisabled();
    await userEvent.type(
      screen.getByLabelText("Resolution notes"),
      "Received corrected invoice",
    );
    await userEvent.click(resolve);
    expect(
      await screen.findByText(/Resolved · Document #3/),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Resolution: Received corrected invoice"),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reload task" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Resolution notes")).toHaveValue(
        "Received corrected invoice",
      ),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Back to review queue/ }),
    );
    expect(
      await screen.findByText(/No review tasks match/),
    ).toBeInTheDocument();
    await userEvent.selectOptions(
      screen.getByLabelText("Filter by status"),
      "resolved",
    );
    expect(
      await screen.findByRole("button", {
        name: /carrier-invoice.pdf.*Resolved/,
      }),
    ).toBeInTheDocument();
  });
  it("keeps operator notes visible after a failed save", async () => {
    installApi();
    render(<ReviewQueue />);
    await userEvent.click(
      await screen.findByRole("button", { name: /carrier-invoice.pdf/ }),
    );
    await screen.findByRole("button", { name: "Start review" });
    await userEvent.type(
      screen.getByLabelText("Review notes"),
      "Do not lose this note",
    );
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json(
          { error: { message: "Task changed; reload before saving" } },
          { status: 409 },
        ),
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Save notes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "reload before saving",
    );
    expect(screen.getByLabelText("Review notes")).toHaveValue(
      "Do not lose this note",
    );
  });
});
