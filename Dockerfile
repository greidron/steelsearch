FROM rust:1.76-bookworm AS builder

WORKDIR /workspace
COPY . .
RUN cargo build --release -p os-node --bin steelsearch

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --system --uid 10001 --gid 0 --home-dir /var/lib/steelsearch steelsearch \
    && mkdir -p /var/lib/steelsearch \
    && chown -R steelsearch:0 /var/lib/steelsearch

COPY --from=builder /workspace/target/release/steelsearch /usr/local/bin/steelsearch

USER steelsearch
EXPOSE 9200 9300

ENTRYPOINT ["/usr/local/bin/steelsearch"]
CMD ["--http.host", "0.0.0.0", "--http.port", "9200", "--transport.host", "0.0.0.0", "--transport.port", "9300", "--path.data", "/var/lib/steelsearch"]
