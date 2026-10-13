import { buildApp } from "./app.js";
import { configSchema } from "./config.js";
import { createPool } from "./db.js";

const config = configSchema.parse(process.env);
const pool = createPool(config.REVIEW_DATABASE_URL);
const { app, repository } = buildApp(pool, config.LOG_LEVEL);
let running: Promise<void> | undefined;
let stopping = false;
function reconcile() {
  if (stopping || running) return;
  running = repository
    .reconcile()
    .then((created) => {
      if (created) app.log.info({ created }, "Recovered review tasks");
    })
    .catch(() => {
      app.log.warn(
        { code: "reconciliation_failed" },
        "Review reconciliation will retry",
      );
    })
    .finally(() => {
      running = undefined;
    });
}
const interval = setInterval(reconcile, config.RECONCILE_INTERVAL_MS);
interval.unref();
app.addHook("onClose", async () => {
  stopping = true;
  clearInterval(interval);
  await running;
  await pool.end();
});
for (const signal of ["SIGTERM", "SIGINT"] as const) {
  process.once(signal, () => {
    const deadline = setTimeout(() => process.exit(1), 15000);
    deadline.unref();
    void app.close().catch(() => {
      process.exitCode = 1;
    });
  });
}
try {
  await app.listen({ host: config.HOST, port: config.PORT });
  reconcile();
} catch {
  app.log.fatal({ code: "startup_failed" }, "Review service could not start");
  await app.close();
  process.exitCode = 1;
}
