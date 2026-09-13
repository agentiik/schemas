# Changelog

The releases of `schemas`.

Every repository of the project carries the same version and is tagged at the same moment, even where nothing changed, so an entry here may say that nothing was built. [Versioning](https://agentiik.github.io/docs#versioning) sets out why, and what a version promises before and after `1.0.0`.

`0.y.z` promises nothing beyond itself: what a release here describes may be gone in the next one.

## v0.1.1, 2026-09-13

This file, and nothing else.

`v0.1.0` was tagged before its changelog was written, and the fix for that is not to move the tag. Within minutes of the push, `sum.golang.org` had recorded the tagged commit of `agentiik` and `bricks` in a public append-only log and `proxy.golang.org` had cached it, so moving `v0.1.0` would have left `go get` serving the old code for ever and made a direct fetch fail with a checksum mismatch that reads as a supply-chain attack. A tag is a name somebody else pins, and a name that quietly comes to mean something else is worse than a second name.

So `v0.1.0` stays exactly where it is, describing exactly what it shipped, and this release adds the description. Every repository gets it at the same version on the same day, as every release here does. From now on a version's entry is merged before its tag is placed, which is written down in the conventions the documentation fixes.

## v0.1.0, 2026-09-12

The contract, released before anything reads it.

- `workflow.schema.json` describes `agentiik.yaml`: `apiVersion`, `kind`, `metadata`, `inputs`, `outputs`, `on`, `mcp`, `include`, `vars`, `secrets`, `defaults`, `concurrency`, `timeout` and `steps`, with every step keyword the language defines.
- `brick.schema.json` describes `/agk/brick.yaml`, the manifest an image carries to become a brick: its ports, its parameters, the secrets it expects and what it needs from the container it is given.
- `envelope.schema.json` describes what travels on a port: `meta` with `run_id`, `step`, `port`, `attempt`, `count` and `produced_at`, and the items with their identities, payloads and attached files.

Every keyword carries a `description` and `examples`, and the build fails without them, because the language reference on the site is a projection of these documents rather than a second description of the same thing.

Fixtures come with them, valid and invalid, and `tools/check.py` holds each schema to its own: a document under `fixtures/<kind>/valid/` must be accepted and one under `invalid/` must be refused. Workflow documents are loaded as YAML 1.2, because a YAML 1.1 parser reads the bare key `on:` as the boolean true and `on:` is how the language spells the trigger block.

Where the documentation states a rule the schema states it, where the documentation is silent the schema takes the reading that cannot contradict it, and the readings that had to be taken are written down in the README rather than left in the files to be discovered.
