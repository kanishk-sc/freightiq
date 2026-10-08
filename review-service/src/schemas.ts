import { z } from "zod";

export const statusSchema = z.enum(["pending", "in_review", "resolved"]);
const idSchema = z.coerce.number().int().positive().max(2147483647);
export const paramsSchema = z.object({ id: idSchema });
export const listSchema = z
  .object({
    status: statusSchema.optional(),
    page: z.coerce.number().int().min(1).max(100000).default(1),
    page_size: z.coerce.number().int().min(1).max(100).default(20),
  })
  .strict();
export const createSchema = z
  .object({
    document_id: z.number().int().positive().max(2147483647),
    reason: z.string().trim().min(1).max(2000).optional(),
  })
  .strict();
export const patchSchema = z
  .object({
    version: z.number().int().positive().max(2147483647),
    status: statusSchema.optional(),
    notes: z.string().trim().max(10000).optional(),
    resolution: z.string().trim().max(10000).optional(),
  })
  .strict()
  .refine(
    (value) =>
      value.status !== undefined ||
      value.notes !== undefined ||
      value.resolution !== undefined,
    { message: "Provide status, notes or resolution" },
  );

export type Status = z.infer<typeof statusSchema>;
export type Patch = z.infer<typeof patchSchema>;
export type ListQuery = z.infer<typeof listSchema>;

export interface Task {
  id: number;
  document_id: number;
  status: Status;
  reason: string;
  notes: string;
  resolution: string;
  version: number;
  created_at: Date;
  updated_at: Date;
  in_review_at: Date | null;
  resolved_at: Date | null;
}

export interface TaskSummary extends Task {
  original_filename: string;
  invoice_id: number | null;
  invoice_number: string | null;
  carrier_name: string | null;
  error_code: string | null;
}
