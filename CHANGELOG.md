# Changelog

The releases of `schemas`.

Every repository of the project carries the same version and is tagged at the same moment, even where nothing changed, so an entry here may say that nothing was built. [Versioning](https://agentiik.github.io/docs#versioning) sets out why, and what a version promises before and after `1.0.0`.

`0.y.z` promises nothing beyond itself: what a release here describes may be gone in the next one.

## Unreleased

- `wire.schema.json` describes the identity and access records: `principal` and `principalRef`, `credential`, `apiToken`, `accessGrant`, `role`, `permission`, `namespaceRecord` with its `quotas`, and `authPolicy`, with fixtures for each.
- `openapi.json` describes the access routes of v0.3.0: passkey and password sign-in, `agk login`'s exchange, the authentication policy, `/me` and its credentials, users, groups, service accounts, namespaces and quotas, grants and API tokens, referring to `wire.schema.json` for every record.
- `tools/check.py` validates `openapi.json` and fails where its routes and the documentation's route table disagree.
- `role`, `permission` and `accessGrant` follow the settled roles: `operator` follows runs with `run:read`, `owner` alone holds `workflow:delete`, `secret:use` is checked at the push, and the documentation's deny takes `run:read_data` from an `editor`; `openapi.json`'s grant and `/me` examples tell the same story.
- The identity records follow what the tables settled: `installation` is refused as a login beside `operator`, a namespace from before v0.3.0 has no `owner`, a user answers `last_sign_in_at`, an API token is never a group's, a passkey's kind is derived from Backup Eligibility alone, and `max_concurrent_tasks` and `max_retention_days` always hold a value.
- `notification` moves to `wire.schema.json`, as a record the API keeps and a route dismisses, and gains `passkey_counter_refused`: a sign-in refused for a passkey's signature counter, carrying the passkey's `credential` rather than a namespace and a grant.
- `openapi.json` follows the settled route table: `DELETE /api/v1/me/credentials/{id}` replaces the query parameter form, and `DELETE /api/v1/me/notifications/{id}`, `GET` and `DELETE` on `/api/v1/namespaces/{ns}`, `/api/v1/users/{login}` and `/api/v1/groups/{group}` are described; the passkey counter rule, the audit actions of groups, members and service accounts, what owning a namespace means, and a policy on an installation addressed by an IP address are in the descriptions.
- `user.suspended_for` says why the policy suspended an account, `no_passkey`, and only beside `suspended: true`.
- `notification` gains `break_glass_recovery`, carrying the `login` of the administrator `agentiik-api recover` issued a recovery code, told to every administrator; `admin_access_widened` covers a grant written by the installation's power and a group joined or left.
- `actor` accepts `installation`, which writes the owner grant of a user's personal namespace at their first sign-in.
- `authPolicy`, `apiToken.principal` and `quotas.max_run_duration` describe what the merged API does: a password session only enrols wherever a passkey is required, no token is minted for `NS/agentiik`, and a run is held to `max_run_duration` rather than refused.
- The root `timeout` of `workflow.schema.json` is held to `max_run_duration` rather than refused, and a workflow writing none is bounded by it.
- `openapi.json` describes `POST /api/v1/auth/sign-out`, `GET /auth/assets/{name}`, `POST /api/v1/auth/password/enrol`, `PUT` and `DELETE /api/v1/me/password`, and `POST /api/v1/me/totp`, `POST /api/v1/me/totp/confirm` and `DELETE /api/v1/me/totp`.
- `openapi.json` follows the merged API on every access route: the 10-minute proof as 403 with RFC 9470's `WWW-Authenticate`, 429 and 503 on the password routes, 400 for two credentials and for a body sent where none is read, the origin rule of a session, the exchange's 403 and 409, a token's 409 at 100 live ones and 422 for `NS/agentiik`, the lockout 409 on the policy, grants and memberships, and a user created from a login alone.
- `tools/check.py` names the statistics routes of v0.6.0 in `NOT_DESCRIBED_YET`.
- `stats` joins the words a namespace and a login may not be, for v0.6.0's `GET /api/v1/stats/pools`; the API still serves a namespace of that name made before v0.3.0, with nothing to do.
- `createUser` says an administrator the bootstrap token creates is given the owner role on every namespace no record names an owner of.
- A namespace's name, a login, a group's name and each half of a service account's are at most 255 characters, inside the wire's references too, and `tools/check.py` holds every copy of the bound together.
- `notification` gains `act`, which of `granted`, `deny_lifted`, `joined_group`, `left_group` and `group_removed` widened access, and `by`, a login or `operator`, and `login` names the user put in on `joined_group` alone.
- `openapi.json` says anybody put in a group is told of, and the other administrators as well where nobody owns.
- `openapi.json` says `GET /api/v1/me` leaves out a workflow its caller holds nothing in.
- `POST /api/v1/auth/passkey/options` answers 503 with `Retry-After` while 10,000 challenges are open across the installation.
- A deny of `grant:manage` on a workflow is refused with 422.
- `user.display_name` is one line holding no control character, as the API holds it.
- A name the workflow file writes is at most 255 characters wherever the grammar is copied, and a port or a workflow output 250 in the workflow file and the manifest; `tools/check.py` holds the copies together.
- Each half of a workflow reference, an include's or a sub-workflow call's, is at most 255 characters, counted in its pattern and held by `tools/check.py`.

## v0.2.5, 2026-09-26

- Nothing changed here. The version moves because every repository carries the same one, which [Versioning](https://agentiik.github.io/docs#versioning) sets out.

## v0.2.4, 2026-09-26

- Nothing changed here. The version moves because every repository carries the same one, which [Versioning](https://agentiik.github.io/docs#versioning) sets out.

## v0.2.3, 2026-09-26

- Nothing changed here. The version moves because every repository carries the same one, which [Versioning](https://agentiik.github.io/docs#versioning) sets out.

## v0.2.2, 2026-09-26

- Nothing changed here. The version moves because every repository carries the same one, which [Versioning](https://agentiik.github.io/docs#versioning) sets out.

## v0.2.1, 2026-09-26

Nothing changed here. The version moves because every repository carries the same one, which [Versioning](https://agentiik.github.io/docs#versioning) sets out.

## v0.2.0, 2026-09-26

### Wire

- `wire.schema.json` describes every message between the controller, the bus, the runner and the API: the task message and result, a runner's registration and heartbeat, the grant redemption, a log shipment, and a runner pool with its join token. Twelve invalid fixtures pin what the shapes refuse: no secret value, input URL or image tag in a task message, no run state in a task result, no private key in a registration.
- Run and task identifiers hold their alphabet and not a length, so the task message the documentation prints is accepted, and is a fixture.
- A task result carries all nine task states, `timed_out` and `cancelled` among them.
- A log is addressed `agk://log/<run>/<task>`, the task escaped as a path segment, and every example and fixture escapes the key it sits beside.
- An idempotency key a fan-out produced has five segments, the shard carrying its cardinality.
- The task message carries `script`, `before_script`, `after_script`, `shell`, `files`, `timeout`, `idempotent` and `cache_key`, so it can describe a script step.
- `files[].to` is optional, and `from` holds a path or a glob.
- `taskMessage.grant` says the redemption answers the tree's URLs too.
- The two grant redemption patterns no RE2 engine could compile are rewritten, the lookahead as a `not`.
- `$defs/secretMount` is the one grammar of a secret mount in the brick manifest, the task message and the redemption: `^/agk/secrets/[A-Za-z0-9][A-Za-z0-9._-]*$`.
- `$defs/stop` is the message on `agentiik.stops`: a task's idempotency key and a reason of `superseded`, `sibling_failed`, `deadline` or `cancelled`.
- `$defs/runnerRotation` is the exchange behind `POST /api/v1/runners/rotate`.
- `$defs/taskProgress` carries `running` and `publishing`, apart from a result's `state`.
- `runnerHeartbeat.response.cancel` names each key whose bound dispatch ended `cancelled` or `timed_out`, never a lost one, as the backstop for a stop on `agentiik.stops`.
- A `timed_out` or `cancelled` task reports the exit code its stop left, a broken output contract reports 121, and a task that did not succeed publishes no port.
- In `taskResult.usage`, `cpu_seconds` and `max_rss_bytes` are optional and travel together, and `image_pull_ms` stays required. `max_rss_bytes` is the largest sample read.
- `taskMessage.runs_on` with an empty list goes to the pool `default`.
- `taskResult.log.truncated` covers the cap, an unanswered closing chunk and a log resumed after a restart.
- A log shipment's `accepted` and `next_seq` describe a chunk past a gap and a chunk after the cap.

### Workflow file and brick manifest

- The root `secrets` block is a list of names, `secrets: [billing]`: the namespace declares each secret's provider and path. `$defs/secret` is gone.
- `$defs/namespace` refuses the words the API's first path segment routes on: `auth`, `me`, `users`, `groups`, `service-accounts`, `namespaces`, `runners`, `runner-pools`, `bus`, `tasks`, `bricks`, `runs` and `artifacts`.
- `$defs/runsOn`: a step goes to the one pool whose labels include every label, and fails with 125 on none or several.
- `network: internal` is described as a network of the task's own, with no route out and no address of the runner host, in the wire, the workflow file and the manifest.

### Build

- `tools/check.py` reads the fixtures again, having validated none since the wire, and fails a group it skips. A fixture group may name a member of a document.
- The build compares the copies of a grammar two documents share and names both pointers when one moves.
- A sixth check refuses a pattern an RE2 engine cannot compile.

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
