import type { FastifyInstance } from "fastify";
import {
  createSchema,
  listSchema,
  paramsSchema,
  patchSchema,
} from "./schemas.js";
import type { ReviewService } from "./service.js";

export function registerRoutes(app: FastifyInstance, service: ReviewService) {
  const repository = service.repository;
  app.get("/health", async () => ({ status: "ok" }));
  app.get("/ready", async () => {
    await repository.ready();
    return { status: "ready" };
  });
  app.get("/api/review-tasks", async (request) =>
    repository.list(listSchema.parse(request.query)),
  );
  app.get("/api/review-tasks/:id", async (request) =>
    repository.get(paramsSchema.parse(request.params).id),
  );
  app.get("/api/review-tasks/:id/history", async (request) =>
    repository.history(paramsSchema.parse(request.params).id),
  );
  app.post("/api/review-tasks", async (request, reply) => {
    const body = createSchema.parse(request.body);
    const result = await repository.create(body.document_id, body.reason);
    return reply
      .code(result.created ? 201 : 200)
      .send({ ...result.task, replayed: !result.created });
  });
  app.patch("/api/review-tasks/:id", async (request) =>
    service.update(
      paramsSchema.parse(request.params).id,
      patchSchema.parse(request.body),
    ),
  );
}
