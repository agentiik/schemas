# Changelog

The releases of `schemas`.

Every repository of the project carries the same version and is tagged at the same moment, even where nothing changed, so an entry here may say that nothing was built. [Versioning](https://agentiik.github.io/docs#versioning) sets out why, and what a version promises before and after `1.0.0`.

`0.y.z` promises nothing beyond itself: what a release here describes may be gone in the next one.

## Unreleased

**The build reads the fixtures again.** Since the wire, `tools/check.py` kept its documents by file name and looked each fixture group up by message name, so it validated no fixture at all and still said everything checked out. It looks the group up by its file now and fails a group it skips. The one fixture that went stale meanwhile, a task result in `cancelled`, which is a task state too since the nine, now says `queued`.

**A secret mount has one grammar.** The brick manifest and the task message accepted `/agk/secrets/client.key` and the grant redemption refused it, so the engine could dispatch a mount a strict runner then could not write; the first two also accepted `/agk/secrets/..`. All three now read `^/agk/secrets/[A-Za-z0-9][A-Za-z0-9._-]*$`, written once in the wire as `$defs/secretMount`: a dot inside a name is kept and a name made of dots is refused.

**A workflow names its secrets and nothing more.** The root `secrets` block is a list of names, `secrets: [billing]`, and no longer says where a value lives: the namespace declares each secret's provider and path, through the API or `agentiik_secret` and under `secret:write`, and is confined to its own paths. `$defs/secret` goes, and every example and fixture that wrote a provider or a path moves.

**The grant names the tree.** `taskMessage.grant` now says the redemption answers the tree's URLs too, as `grantRedemption` already required.

**A schema every engine can read.** Two patterns in the grant redemption could not be compiled by any RE2 engine: one used a negative lookahead to say that a path holds no parent segment, and the other wrote the null character the ECMA-262 way. JSON Schema says `pattern` is ECMA-262 and both are legal there, but Go, Rust and everything else built on RE2 refuse the whole document rather than the one keyword, so the wire was a schema only Python could read. Found the first time something outside this repository compiled it, which was a conformance test in the engine. The lookahead becomes a `not` beside the pattern, which says the same thing to everybody, and the build gains a sixth check so it cannot come back.

**A task message names everything the runner needs, and now it can.** The message could not describe a step whose image is a base image rather than a brick: `script`, `before_script`, `after_script` and `shell` had nowhere to be written, and neither did `files`, `timeout`, `idempotent` or `cache_key`. A closed document refuses what it does not name, so the wire was refusing the engine's own step kind. All eight arrive, with a fixture that is a script step end to end. None of them is a payload or a secret: a command is what the workflow author wrote in `agentiik.yaml`, and the bytes of a file are still fetched from the tree by redeeming the grant.

**The idempotency key is five segments where a fan-out produced it.** The pattern admitted four, which was neither what the page prints, nor what the engine mints, nor what the database generates. A shard is an index and a cardinality, `AGK_SHARD` carries `3/8`, and a key that dropped the `8` could not say which fan-out it belonged to: the third of eight and the third of six are different units of work with one name. Every example and every fixture that wrote a four-segment key moves, and the fixture named for a fan-out now carries the shard it was named for and did not have.

**A log has a URI of its own.** The wire pinned a log's address as `^agk://run/`, which is where an artifact lives, and left the rest unpinned because the documentation's printed example, `agk://run/<run>/<step>/log`, could not be right: a step fanned out into eight shards has eight logs and that address names no shard. The answer is that a log is not addressed like an artifact at all. The scheme names a kind in its first segment, and a log is its own: `agk://log/<run>/<task>`. A log belongs to one task, and a task identifier tells eight shards apart exactly, that being what a task identifier is for. The task carries slashes, so it is escaped as a path segment. Both places the wire names a log URI move, with their examples and the seven fixtures that carry one.

**A task result can say it timed out.** The wire took the seven task states the page drew and the engine has produced nine since v0.1.0: a task stopped at its deadline and a task stopped by a cancellation are neither of them `failed`. So a runner could produce a result the controller would refuse. The page names all nine now and the enumeration follows it, with the four endings told apart in the description because a retry policy reads the cause.

**The wire accepts the page it was written from.** The first version imposed twenty-six characters on a run and task identifier, which is what the engine mints, and so refused the task message the documentation prints, in four places at once: its `task_id`, its `run_id`, its idempotency key and its grant. The page elides identifiers deliberately, to fifteen and twelve characters, and `envelope.schema.json` had already settled the question and written down why. The alphabet is held and the length is not, the same reading in both documents, and the message the page prints is now a fixture so that the next version cannot refuse it either.

**The wire, written down first.** `wire.schema.json` describes every message that travels between the controller, the bus, the runner and the API: the task message and the task result, a runner's registration, its ten second heartbeat, the redemption of a task's grant, a log shipment, and a runner pool with the token issued from it. One document rather than one per message, because they share a vocabulary and a `$ref` may not leave a document here, so the run and task states, the identifiers, the digests and the idempotency key are written once and referenced.

What the shapes refuse is the point. A task message carries no secret value, no input URL and no image tag, and the objects are closed so that none of the three can be written at all rather than merely being undocumented. A task result ends in a task state and never a run state. A registration carries the public key and has no room for the private one. Twelve invalid fixtures pin those refusals, one rule each.

`tools/check.py` grew two things to hold it: a fixture group may name a member of a document rather than a whole document, so a fixture still pins one message, and a document that is a family has no instance at its root to illustrate.

## v0.1.2, 2026-09-13

Nothing changed here. The version moves because every repository carries the same one, which [Versioning](https://agentiik.github.io/docs#versioning) sets out.

The release is documentation: a [Get started](https://agentiik.github.io/docs#get-started) chapter at the top of the site, written from a run against `v0.1.1` rather than from what the rest of the page promises, and a recorded session of the command line on the home page.

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
