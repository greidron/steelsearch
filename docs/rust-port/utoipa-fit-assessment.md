# Utoipa Fit Assessment

This document records the practical fit of `utoipa` for Steelsearch.

## Short Answer

`utoipa` is a good Rust OpenAPI candidate, but Steelsearch should not do a
blind full rewrite from inventory-generated OpenAPI to handler-local
annotations in one pass.

## Why

Steelsearch uses:

- a custom `RestRequest` / `RestResponse` layer;
- runtime dispatch in `os-node`;
- generated source inventories;
- evidence-profile ownership used in release/audit flows.

That is different from a framework-first `axum` / `actix-web` application where
annotation-first OpenAPI is the natural source of truth.

## Recommended Position

Short term:

- keep generated `openapi.json` as the exhaustive route inventory surface;
- keep Swagger serving backed by that generated spec;
- add drift tests so generated OpenAPI is release-auditable.

Medium term:

- use `utoipa` selectively on stable route families;
- compare `utoipa` output and generated inventory output before expanding.

## Current Proof Of Concept

There is now a minimal compile-time `utoipa` proof in:

- [utoipa_poc.rs](/home/ubuntu/steelsearch/crates/os-node/tests/utoipa_poc.rs)

It demonstrates:

- route-local path annotation;
- schema derivation;
- OpenAPI `3.0.3` generation for representative routes.
