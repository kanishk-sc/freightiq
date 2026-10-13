import type { Pool, PoolClient } from "pg";
import { transaction } from "./db.js";
import { ApiError } from "./errors.js";
import type { ListQuery, Task, TaskSummary } from "./schemas.js";

const summarySelect = `SELECT r.*, d.original_filename, i.id AS invoice_id,
  i.invoice_number, i.carrier_name, j.error_code
  FROM review_tasks r JOIN documents d ON d.id = r.document_id
  LEFT JOIN invoices i ON i.document_id = d.id
  LEFT JOIN processing_jobs j ON j.document_id = d.id`;

// Only durable document-specific failures qualify, never broker/config/network failures.
const signalSelect = `SELECT d.id AS document_id,
  CASE WHEN EXISTS (SELECT 1 FROM audit_flags f JOIN invoices i ON i.id = f.invoice_id
                    WHERE i.document_id = d.id)
       THEN 'Invoice audit flagged missing fields or invalid values'
       ELSE 'Document processing requires manual review: ' || j.error_code END AS reason
  FROM documents d LEFT JOIN processing_jobs j ON j.document_id = d.id
  WHERE (EXISTS (SELECT 1 FROM audit_flags f JOIN invoices i ON i.id = f.invoice_id
                 WHERE i.document_id = d.id)
    OR (j.status = 'failed' AND j.error_code IN
        ('extraction_validation_failed', 'pdf_has_no_text', 'pdf_parse_failed')))`;

export async function appendHistory(
  client: PoolClient,
  task: Task,
  from: string | null,
  origin: string,
) {
  await client.query(
    `INSERT INTO review_history
    (task_id, from_status, to_status, notes, resolution, version, origin)
    VALUES ($1, $2, $3, $4, $5, $6, $7)`,
    [
      task.id,
      from,
      task.status,
      task.notes,
      task.resolution,
      task.version,
      origin,
    ],
  );
}

export class ReviewRepository {
  constructor(public pool: Pool) {}

  async list(query: ListQuery) {
    return transaction(this.pool, async (client) => {
      await client.query(
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
      );
      const filter = query.status ?? null;
      const count = await client.query<{ total: number }>(
        "SELECT count(*)::int AS total FROM review_tasks WHERE ($1::text IS NULL OR status = $1)",
        [filter],
      );
      const rows = await client.query<TaskSummary>(
        `${summarySelect}
        WHERE ($1::text IS NULL OR r.status = $1)
        ORDER BY r.created_at DESC, r.id DESC LIMIT $2 OFFSET $3`,
        [filter, query.page_size, (query.page - 1) * query.page_size],
      );
      return {
        items: rows.rows,
        total: count.rows[0]!.total,
        page: query.page,
        page_size: query.page_size,
      };
    });
  }

  async get(id: number) {
    const result = await this.pool.query<TaskSummary>(
      `${summarySelect} WHERE r.id = $1`,
      [id],
    );
    if (!result.rows[0])
      throw new ApiError(404, "task_not_found", "Review task not found");
    return result.rows[0];
  }

  async history(id: number) {
    await this.get(id);
    const result = await this.pool.query(
      `SELECT id, task_id, from_status, to_status,
      notes, resolution, version, origin, created_at FROM review_history WHERE task_id = $1 ORDER BY id`,
      [id],
    );
    return result.rows;
  }

  async create(documentId: number, reason?: string) {
    return transaction(this.pool, async (client) => {
      const document = await client.query(
        "SELECT id FROM documents WHERE id = $1 FOR KEY SHARE",
        [documentId],
      );
      if (!document.rowCount)
        throw new ApiError(404, "document_not_found", "Document not found");
      const existing = await client.query<Task>(
        "SELECT * FROM review_tasks WHERE document_id = $1",
        [documentId],
      );
      if (existing.rows[0]) return { task: existing.rows[0], created: false };
      const signals = await client.query<{ reason: string }>(
        `${signalSelect} AND d.id = $1`,
        [documentId],
      );
      const taskReason = reason ?? signals.rows[0]?.reason;
      if (!taskReason)
        throw new ApiError(
          422,
          "no_review_signal",
          "Provide a reason for a document without audit findings",
        );
      const inserted = await client.query<Task>(
        `INSERT INTO review_tasks (document_id, reason)
        VALUES ($1, $2) ON CONFLICT (document_id) DO NOTHING RETURNING *`,
        [documentId, taskReason],
      );
      const task = inserted.rows[0];
      if (task) {
        await appendHistory(
          client,
          task,
          null,
          reason ? "operator" : "pipeline",
        );
        return { task, created: true };
      }
      const replay = await client.query<Task>(
        "SELECT * FROM review_tasks WHERE document_id = $1",
        [documentId],
      );
      return { task: replay.rows[0]!, created: false };
    });
  }

  async reconcile() {
    // A single statement atomically creates tasks AND initial history, including
    // when several Node instances sweep concurrently. Resolved tasks stay closed.
    const result = await this.pool.query(`WITH candidates AS (
      ${signalSelect}
      AND NOT EXISTS (SELECT 1 FROM review_tasks r WHERE r.document_id = d.id)
      ORDER BY d.id LIMIT 100
    ), inserted AS (
      INSERT INTO review_tasks (document_id, reason)
      SELECT document_id, reason FROM candidates
      ON CONFLICT (document_id) DO NOTHING RETURNING *
    ) INSERT INTO review_history
      (task_id, from_status, to_status, notes, resolution, version, origin)
      SELECT id, NULL, status, notes, resolution, version, 'pipeline' FROM inserted
      RETURNING task_id`);
    return result.rowCount ?? 0;
  }

  async ready() {
    await this.pool.query("SELECT id FROM review_tasks LIMIT 0");
    await this.pool.query("SELECT id FROM review_history LIMIT 0");
  }
}
