FROM golang:1.24-bookworm AS build

# The community registry image is no longer available. Build the same release
# from its immutable upstream commit instead of depending on a mutable tag.
RUN CGO_ENABLED=0 go install github.com/minio/minio@07c3a429bfed433e49018cb0f78a52145d4bedeb

FROM debian:bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /go/bin/minio /usr/local/bin/minio
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
