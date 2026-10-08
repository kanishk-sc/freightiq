import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import pg from "pg";
import { buildApp } from "../src/app.js";
import { createPool } from "../src/db.js";

const databaseUrl =
  process.env.TEST_DATABASE_URL ??
  "postgresql://freightiq:freightiq@localhost:5433/freightiq_review_test";
if (!new URL(databaseUrl).pathname.endsWith("_test"))
  throw new Error("Tests require a disposable database ending in _test");
const pool = createPool(databaseUrl);
const { app, repository } = buildApp(pool);
beforeAll(async () => {
  await repository.ready();
  await app.ready();
});
beforeEach(async () => {
  await pool.query(
    "TRUNCATE review_history, review_tasks, audit_flags, line_items, processing_jobs, invoices, documents RESTART IDENTITY CASCADE",
  );
});
afterAll(async () => {
  await app.close();
  await pool.end();
});

async function document(flagged = false) {
  const result = await pool.query<{ id: number }>(
    `INSERT INTO documents
    (object_key, original_filename, content_type, size_bytes, sha256)
    VALUES ($1, 'carrier-invoice.pdf', 'application/pdf', 100, $2) RETURNING id`,
    [crypto.randomUUID(), "a".repeat(64)],
  );
  const id = result.rows[0]!.id;
  if (flagged) {
    const invoice = await pool.query<{ id: number }>(
      "INSERT INTO invoices (document_id, audited, carrier_name) VALUES ($1, true, 'North Freight') RETURNING id",
      [id],
    );
    await pool.query(
      "INSERT INTO audit_flags (invoice_id, field, severity, description) VALUES ($1, 'invoice_number', 'error', 'Required field invoice_number is missing')",
      [invoice.rows[0]!.id],
    );
  }
  return id;
}
async function create(documentId: number, reason?: string) {
  return app.inject({
    method: "POST",
    url: "/api/review-tasks",
    payload: { document_id: documentId, ...(reason ? { reason } : {}) },
  });
}
async function patch(id: number, payload: object) {
  return app.inject({
    method: "PATCH",
    url: `/api/review-tasks/${id}`,
    payload,
  });
}

describe("review API backed by PostgreSQL", () => {
  it("reports health and schema readiness", async () => {
    expect((await app.inject("/health")).json()).toEqual({ status: "ok" });
    expect((await app.inject("/ready")).statusCode).toBe(200);
  });
  it.each([
    { document_id: "1" },
    { document_id: -1 },
    { document_id: 2147483648 },
    { document_id: 1, reason: " " },
    { document_id: 1, secret: "unexpected" },
  ])("validates create input: %j", async (payload) => {
    const response = await app.inject({
      method: "POST",
      url: "/api/review-tasks",
      payload,
    });
    expect(response.statusCode).toBe(400);
    expect(response.json().error.code).toBe("validation_error");
  });
  it("validates query and route parameters", async () => {
    for (const url of [
      "?status=other",
      "?page=0",
      "?page_size=101",
      "/bad-id",
      "/0",
    ]) {
      expect((await app.inject(`/api/review-tasks${url}`)).statusCode).toBe(
        400,
      );
    }
    expect((await app.inject("/missing")).json().error.code).toBe(
      "route_not_found",
    );
  });
  it("rejects missing documents and clean documents without a manual reason", async () => {
    expect((await create(999)).statusCode).toBe(404);
    expect((await create(await document())).statusCode).toBe(422);
  });
  it("creates and reads a real task with initial history", async () => {
    const response = await create(await document(true));
    expect(response.statusCode).toBe(201);
    const task = response.json();
    expect(task.status).toBe("pending");
    expect(task.version).toBe(1);
    const detail = (await app.inject(`/api/review-tasks/${task.id}`)).json();
    expect(detail.original_filename).toBe("carrier-invoice.pdf");
    expect(detail.carrier_name).toBe("North Freight");
    const events = (
      await app.inject(`/api/review-tasks/${task.id}/history`)
    ).json();
    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({
      from_status: null,
      to_status: "pending",
      origin: "pipeline",
    });
  });
  it("deduplicates concurrent creates without duplicating history", async () => {
    const id = await document(true);
    const results = await Promise.all([create(id), create(id), create(id)]);
    expect(results.map((r) => r.statusCode).sort()).toEqual([200, 200, 201]);
    expect(new Set(results.map((r) => r.json().id)).size).toBe(1);
    expect((await pool.query("SELECT * FROM review_history")).rowCount).toBe(1);
  });
  it("persists transitions, notes, timestamps and ordered audit snapshots", async () => {
    const task = (
      await create(await document(), "Operator requested follow-up")
    ).json();
    const first = await patch(task.id, {
      version: 1,
      status: "in_review",
      notes: "Contacting carrier",
    });
    expect(first.statusCode).toBe(200);
    expect(first.json().in_review_at).not.toBeNull();
    const second = await patch(task.id, {
      version: 2,
      status: "resolved",
      resolution: "Carrier supplied missing invoice number",
    });
    expect(second.statusCode).toBe(200);
    const stored = (
      await pool.query("SELECT * FROM review_tasks WHERE id = $1", [task.id])
    ).rows[0];
    expect(stored).toMatchObject({
      status: "resolved",
      version: 3,
      resolution: "Carrier supplied missing invoice number",
    });
    expect(stored.resolved_at).toBeInstanceOf(Date);
    const events = (
      await app.inject(`/api/review-tasks/${task.id}/history`)
    ).json();
    expect(events.map((event: { version: number }) => event.version)).toEqual([
      1, 2, 3,
    ]);
    expect(events[1].notes).toBe("Contacting carrier");
    expect(events[2].resolution).toBe(stored.resolution);
  });
  it("rejects skipped, backwards, and unresolved transitions", async () => {
    const task = (await create(await document(true))).json();
    expect(
      (
        await patch(task.id, {
          version: 1,
          status: "resolved",
          resolution: "done",
        })
      ).statusCode,
    ).toBe(409);
    await patch(task.id, { version: 1, status: "in_review" });
    expect(
      (await patch(task.id, { version: 2, status: "pending" })).statusCode,
    ).toBe(409);
    expect(
      (await patch(task.id, { version: 2, status: "resolved" })).statusCode,
    ).toBe(422);
    await patch(task.id, {
      version: 2,
      status: "resolved",
      resolution: "Confirmed",
    });
    expect(
      (await patch(task.id, { version: 3, status: "in_review" })).statusCode,
    ).toBe(409);
    expect(
      (await patch(task.id, { version: 3, resolution: " " })).statusCode,
    ).toBe(422);
  });
  it("validates patches, preserves no-ops, and returns 404s", async () => {
    const task = (await create(await document(true))).json();
    for (const payload of [
      { status: "in_review" },
      { version: 1 },
      { version: 1, notes: "x".repeat(10001) },
    ]) {
      expect((await patch(task.id, payload)).statusCode).toBe(400);
    }
    expect(
      (await patch(task.id, { version: 1, status: "pending" })).json().version,
    ).toBe(1);
    expect(
      (await patch(999, { version: 1, notes: "missing" })).statusCode,
    ).toBe(404);
    expect((await app.inject("/api/review-tasks/999/history")).statusCode).toBe(
      404,
    );
  });
  it("prevents lost updates from two operators", async () => {
    const task = (await create(await document(true))).json();
    const replies = await Promise.all([
      patch(task.id, { version: 1, notes: "operator one" }),
      patch(task.id, { version: 1, notes: "operator two" }),
    ]);
    expect(replies.map((reply) => reply.statusCode).sort()).toEqual([200, 409]);
    expect(
      (await pool.query("SELECT count(*)::int AS n FROM review_history"))
        .rows[0].n,
    ).toBe(2);
  });
  it("filters and paginates deterministically, including an empty last page", async () => {
    const first = (await create(await document(true))).json();
    await create(await document(true));
    await create(await document(true));
    await patch(first.id, { version: 1, status: "in_review" });
    const response = (
      await app.inject("/api/review-tasks?status=pending&page_size=1&page=2")
    ).json();
    expect(response).toMatchObject({ total: 2, page: 2, page_size: 1 });
    expect(response.items).toHaveLength(1);
    expect(response.items[0].status).toBe("pending");
    const empty = (
      await app.inject("/api/review-tasks?status=pending&page_size=1&page=3")
    ).json();
    expect(empty).toMatchObject({ total: 2, items: [] });
  });
  it("recovers missed notifications and never resets resolved tasks", async () => {
    const doc = await document(true);
    expect(await repository.reconcile()).toBe(1);
    const task = (await pool.query("SELECT * FROM review_tasks")).rows[0];
    await patch(task.id, { version: 1, status: "in_review" });
    await patch(task.id, {
      version: 2,
      status: "resolved",
      resolution: "Verified",
    });
    expect(await repository.reconcile()).toBe(0);
    expect((await create(doc)).json()).toMatchObject({
      status: "resolved",
      resolution: "Verified",
      replayed: true,
    });
  });
  it("reconciles schema failures but excludes configuration/network failures", async () => {
    for (const code of [
      "extraction_validation_failed",
      "model_configuration_or_output_invalid",
      "model_request_failed",
    ]) {
      await pool.query(
        `INSERT INTO processing_jobs (id, idempotency_key, document_id, status, error_code)
        VALUES ($1, $2, $3, 'failed', $4)`,
        [crypto.randomUUID(), crypto.randomUUID(), await document(), code],
      );
    }
    expect(await repository.reconcile()).toBe(1);
    expect(
      (await pool.query("SELECT reason FROM review_tasks")).rows[0].reason,
    ).toContain("extraction_validation_failed");
  });
  it("rolls back a task edit if its history insert fails", async () => {
    const task = (await create(await document(true))).json();
    await pool.query(`CREATE FUNCTION reject_review_history() RETURNS trigger LANGUAGE plpgsql AS
      $$ BEGIN RAISE EXCEPTION 'private failure text'; END $$;
      CREATE TRIGGER reject_history BEFORE INSERT ON review_history FOR EACH ROW EXECUTE FUNCTION reject_review_history()`);
    try {
      const response = await patch(task.id, {
        version: 1,
        status: "in_review",
      });
      expect(response.statusCode).toBe(503);
      expect(response.body).not.toContain("private failure text");
      expect(
        (await pool.query("SELECT status, version FROM review_tasks")).rows[0],
      ).toEqual({ status: "pending", version: 1 });
    } finally {
      await pool.query(
        "DROP TRIGGER reject_history ON review_history; DROP FUNCTION reject_review_history()",
      );
    }
  });
  it("reports unavailable database without leaking connection details", async () => {
    const unavailable = new pg.Pool({
      connectionString: "postgresql://private:secret@127.0.0.1:1/unavailable",
      connectionTimeoutMillis: 200,
    });
    const { app: broken } = buildApp(unavailable);
    try {
      expect((await broken.inject("/health")).statusCode).toBe(200);
      for (const url of ["/ready", "/api/review-tasks"]) {
        const response = await broken.inject(url);
        expect(response.statusCode).toBe(503);
        expect(response.json().error.code).toBe("service_unavailable");
        expect(response.body).not.toContain("secret");
      }
    } finally {
      await broken.close();
      await unavailable.end();
    }
  });
});
