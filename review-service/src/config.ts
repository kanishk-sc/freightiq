import { z } from "zod";

export const configSchema = z.object({
  REVIEW_DATABASE_URL: z.url().refine((url) => /^postgres(ql)?:\/\//.test(url)),
  HOST: z.string().default("127.0.0.1"),
  PORT: z.coerce.number().int().min(1).max(65535).default(8001),
  LOG_LEVEL: z
    .enum(["fatal", "error", "warn", "info", "debug", "trace", "silent"])
    .default("info"),
  RECONCILE_INTERVAL_MS: z.coerce.number().int().min(1000).default(30000),
});

export type Config = z.infer<typeof configSchema>;
