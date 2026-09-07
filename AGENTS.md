# Release Work

- Follow `docs/releases/README.md` for every new release, including RCs.
- Never create/push a release tag or publish a GitHub release without explicit
  user approval. Compatibility tests and note-format checks are not approval.
- Include generated per-scenario comparisons with the previous published
  release and OpenSearch. Use actual benchmark executable identities, not
  manually inferred before/after labels. Do not omit regressions or scenarios.
- Use `tools/release_notes.py` to generate/check notes and
  `tools/publish-release.py` for publication. Do not bypass validation with
  direct `gh release create`, generated notes, or a separate API call.
- Do not claim that local policy files configure GitHub permissions or prevent
  administrator bypass. Remote enforcement must be verified separately.
