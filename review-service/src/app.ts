import Fastify from "fastify";
import { ZodError } from "zod";
import type { Pool } from "pg";
import { ApiError } from "./errors.js";
import { ReviewRepository } from "./repository.js";
import { registerRoutes } from "./routes.js";
import { ReviewService } from "./service.js";

export function buildApp(pool: Pool, logLevel = "silent") {
  const app = Fastify({
    logger:
      logLevel === "silent"
        ? false
        : {
            level: logLevel,
            // Do not record URLs/query strings, request bodies, or database exception text.
            serializers: { req: (req) => ({ method: req.method, id: req.id }) },
          },
    bodyLimit: 32768,
    requestTimeout: 10000,
  });
  const repository = new ReviewRepository(pool);
  pool.on("error", () =>
    app.log.error(
      { code: "database_pool_error" },
      "Idle database connection failed",
    ),
  );
  app.setErrorHandler(
    (error: Error & { statusCode?: number; code?: string }, request, reply) => {
      const send = (status: number, code: string, message: string) =>
        reply.code(status).send({
          error: { code, message },
          request_id: request.id,
        });
      if (error instanceof ZodError)
        return send(
          400,
          "validation_error",
          "Request parameters or body are invalid",
        );
      if (error instanceof ApiError)
        return send(error.status, error.code, error.message);
      if (
        error.statusCode &&
        error.statusCode >= 400 &&
        error.statusCode < 500
      ) {
        return send(
          error.statusCode,
          "invalid_request",
          "Request could not be parsed",
        );
      }
      app.log.error(
        { code: "dependency_failure", request_id: request.id },
        "Review request failed",
      );
      return send(
        503,
        "service_unavailable",
        "Review service is temporarily unavailable",
      );
    },
  );
  app.setNotFoundHandler((request, reply) =>
    reply.code(404).send({
      error: { code: "route_not_found", message: "Route not found" },
      request_id: request.id,
    }),
  );
  registerRoutes(app, new ReviewService(repository));
  return { app, repository };
}
