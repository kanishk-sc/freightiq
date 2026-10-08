import { transaction } from "./db.js";
import { ApiError } from "./errors.js";
import { appendHistory, ReviewRepository } from "./repository.js";
import type { Patch, Status, Task } from "./schemas.js";

const nextStatus: Record<Status, Status | null> = {
  pending: "in_review",
  in_review: "resolved",
  resolved: null,
};

export class ReviewService {
  constructor(public repository: ReviewRepository) {}

  async update(id: number, patch: Patch) {
    return transaction(this.repository.pool, async (client) => {
      const result = await client.query<Task>(
        "SELECT * FROM review_tasks WHERE id = $1 FOR UPDATE",
        [id],
      );
      const task = result.rows[0];
      if (!task)
        throw new ApiError(404, "task_not_found", "Review task not found");
      if (patch.version !== task.version)
        throw new ApiError(
          409,
          "version_conflict",
          "Task changed; reload before saving",
        );
      const status = patch.status ?? task.status;
      if (status !== task.status && nextStatus[task.status] !== status) {
        throw new ApiError(
          409,
          "invalid_transition",
          "Move Pending to In Review, then In Review to Resolved",
        );
      }
      const notes = patch.notes ?? task.notes;
      const resolution = patch.resolution ?? task.resolution;
      if (status === "resolved" && !resolution.trim()) {
        throw new ApiError(
          422,
          "resolution_required",
          "Resolution notes are required to resolve a task",
        );
      }
      if (
        status === task.status &&
        notes === task.notes &&
        resolution === task.resolution
      )
        return task;
      const updated = await client.query<Task>(
        `UPDATE review_tasks SET status = $2::text, notes = $3,
        resolution = $4, version = version + 1, updated_at = clock_timestamp(),
        in_review_at = CASE WHEN $2 = 'in_review' THEN COALESCE(in_review_at, clock_timestamp()) ELSE in_review_at END,
        resolved_at = CASE WHEN $2 = 'resolved' THEN COALESCE(resolved_at, clock_timestamp()) ELSE resolved_at END
        WHERE id = $1 RETURNING *`,
        [id, status, notes, resolution],
      );
      const saved = updated.rows[0]!;
      await appendHistory(client, saved, task.status, "operator");
      return saved;
    });
  }
}
