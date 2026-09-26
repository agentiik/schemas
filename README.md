# schemas

The contract every other repository reads: JSON Schema 2020-12 documents for the workflow file, the brick manifest, the envelope and the wire, and the OpenAPI document of the API.

This repository carries the same version as every other and is tagged at the same
moment, and every repository that consumes it pins that version: the core, the bricks,
the console, the iOS application and the Android application. A schema change therefore
ships in a release of the whole project, and it lands here first.

What the schemas are written against is the specification at
<https://agentiik.github.io/docs>. Where the documentation states a rule, the schema
states it; where it is silent, the schema takes the reading that cannot contradict it.

## What is in here

| Document | `$id` | Describes |
| --- | --- | --- |
| [`workflow.schema.json`](workflow.schema.json) | `https://schemas.agentiik.dev/workflow.schema.json` | `agentiik.yaml`, the entry point of a workflow repository: `apiVersion`, `kind`, `metadata`, `inputs`, `outputs`, `on`, `mcp`, `include`, `vars`, `secrets`, `defaults`, `concurrency`, `timeout` and `steps`, with every step keyword. |
| [`brick.schema.json`](brick.schema.json) | `https://schemas.agentiik.dev/brick.schema.json` | `/agk/brick.yaml`, the manifest an image carries to become a brick: its ports, its parameters, the secrets it expects and what it needs from the container it is given. |
| [`envelope.schema.json`](envelope.schema.json) | `https://schemas.agentiik.dev/envelope.schema.json` | `{ meta, items }`, the one document that travels along a port. |
| [`wire.schema.json`](wire.schema.json) | `https://schemas.agentiik.dev/wire.schema.json` | Every message between the controller, the bus, the runner and the API: the task message, the progress of the task and its result, a runner's registration, its heartbeat, the rotation of its credential, the redemption of a task's grant, a log shipment, and a runner pool with the token issued from it. Beside them, the identity and access records the API keeps: a principal and the one string that names it, a credential, an API token without its value, a grant, the roles and the permissions, a namespace with its quotas, and the authentication policy. |
| [`openapi.json`](openapi.json) | `https://schemas.agentiik.dev/openapi.json` | The routes of `/api/v1`, so far those of v0.3.0's access: signing in with a passkey or a password, `agk login`'s exchange, the authentication policy, `/me` and the caller's credentials, users and their enrolment, groups and their members, service accounts, namespaces and their quotas, grants at namespace and workflow scope, and API tokens. OpenAPI 3.1, whose schemas are JSON Schema 2020-12. |

`wire.schema.json` is a family rather than one document's shape: a reader validates against the member it is holding, `#/$defs/taskMessage` or `#/$defs/taskResult` and so on. They sit in one document because they share a vocabulary, the run and task states and the identifiers being the same strings everywhere, and because a `$ref` may not leave a document here: an enumeration written twice is an enumeration that drifts. The fixture index names one group per member for the same reason, so a fixture pins one message rather than something the wire allows somewhere.

`openapi.json` is the one document whose `$ref` leaves it, and only for a schema beside it: a user is `wire.schema.json#/$defs/user`, resolved relative to the document as every OpenAPI consumer resolves a reference. The wire is where the access records are defined, and a copy of them here would be the drift the rest of this repository refuses. What the document defines itself is what only a route carries: a request body, a list, a token shown once, and Web Authentication's own JSON forms. A generator reads the two files side by side, or a bundler inlines the wire's definitions first. It describes the routes the documentation's table lists at [#api](https://agentiik.github.io/docs#api), and the build holds the two to each other.

Beside them, [`fixtures/`](fixtures) holds the documents that pin what the schemas accept
and what they refuse, and [`tools/check.py`](tools/check.py) is the check the build runs.

## Running the check

```sh
python -m pip install -r requirements.txt
python tools/check.py
```

No arguments, from anywhere in the repository. It is the same command
[`.github/workflows/validate.yml`](.github/workflows/validate.yml) runs, so a green run
locally means a green run there. Add `-v` to have it name every fixture and say why each
refused one was refused.

Seven things fail the build:

1. a schema that is not a legal JSON Schema 2020-12 document, that does not carry the
   `$id` it is published under, or that holds a `$ref` leading nowhere;
2. a keyword without a `description` or without `examples`;
3. an example that does not validate against the keyword it illustrates;
4. a fixture that does not behave as `fixtures/index.json` says it does;
5. a `pattern` no RE2 engine can compile, which is a lookahead, a lookbehind, a
   backreference or a unicode escape written the ECMA-262 way. JSON Schema says `pattern`
   is ECMA-262 and all four are legal there; Go, Rust and everything else built on RE2
   refuse the whole document rather than the one keyword, and a schema only some consumers
   can read is half a schema. What a lookahead expresses, a `not` beside the pattern
   expresses too;
6. a grammar two documents share, written differently in one of them. A `$ref` may not
   leave a document here, so a grammar the manifest and the wire both hold is two copies,
   and copies that drift let the engine dispatch a secret mount a strict runner then
   refuses to write. The shared grammars, a secret mount, a name the workflow file writes
   and a parameter name, are listed in `ONE_GRAMMAR` in `tools/check.py` with every place each is written. A grammar written inside a longer pattern, the namespace name inside `group:team-finance` or `finance/agentiik`, is listed in `COMPOSED_GRAMMAR` with the template it is written into, and has to read exactly as that template filled in;
7. an em dash, anywhere in any text file.

## Why every keyword carries a description and examples

The language reference on the site and the `workflow.language` MCP tool are both
generated from these documents: every sentence either tool shows is a projection of a
`description` field here, and every example it offers is an entry of an `examples` array
here. A language documented in three places teaches three different languages, and the
failure mode is the worst available, a tool confidently teaching a model syntax that
validation then rejects.

So the rule is the build's job rather than a reviewer's. A keyword with nothing to say
for itself fails the run, and a description that only restates the keyword's own name
fails review.

## Readings taken where the documentation is silent

The sentence at the top of this file cuts both ways. Where the documentation states a
rule the schema states it; where it is silent the schema takes the reading that cannot
contradict it, and a reading nobody wrote down cannot be told from an oversight. So every
one of them is here, saying what the documentation does and does not say and which way
the schema went. Where a consumer reading a schema on its own would need the note, the
same reading is attached to the subschema as a `$comment`; `tools/check.py` ignores
`$comment`, so it costs nothing to carry.

### Grammars the documentation uses without defining

The documentation writes these names and never gives a pattern for them. Each grammar
below is read off the spellings it does write, and is wide enough to admit every one of
them.

| Where | What the documentation gives | Reading taken |
| --- | --- | --- |
| `workflow.$defs/identifier` | Names spelled `monthly-invoicing`, `finance`, `create_invoice`, `orders`, `out`, `rejected`, and the rule that a name travels through a URL, an environment variable and a tool list unchanged. | Letters, digits, hyphens and underscores, first character alphanumeric. It is the grammar every name in the file is keyed on, and `brick.$defs/portName` is the same one so that a port declared in a manifest can be named in a workflow. |
| `workflow.metadata.name` | A workflow name forms the `<namespace>/<name>` identity. Every workflow and namespace it writes is lowercase and hyphenated, and it gives a narrower rule only for a published brick name, which the catalog files a page under. | The identifier grammar, not the brick's. A rule written about a catalog entry is not evidence about a git remote, so the narrower reading would be borrowed rather than read. Recorded as a `$comment` on both names. |
| `workflow.$defs/duration` | Durations written `2s`, `30s`, `10m`, `24h`, `7d`, and a brick parameter pattern in the manifest example spelling `^[0-9]+(ms\|s\|m)$`. | A number and one of `ms`, `s`, `m`, `h`, `d`. The set is assembled from what is written; no other unit appears anywhere. |
| `workflow.$defs/expression` | A CEL expression inside `${{ }}`, and the roots it may read. | An unconstrained string. Which roots exist, and where `item` and `secrets` may be read, is expression-language work rather than shape, so those rules sit with the validator and the fixtures under `refused_by: validator` pin them. |
| `scheduleTrigger.cron` | A five-field cron expression read in the timezone beside it. | Five non-space fields, and nothing about what a field may hold. Refusing a field the documentation never describes would be inventing a dialect. |
| `webhookTrigger.method` | One method, `POST`. | Upper-case letters. An enum would fix a set the documentation never gives. |
| `runsOn` items, `egress.allow` items | Selectors written `zone=dmz`, `arch=amd64`; destinations written `api.billing.example.com:443`. | `key=value` and `host:port`. The port is bounded to 1 through 65535, because the proxy opens a connection to it and there is nothing above that to open. |
| `files[].mode` | One value, `"0444"`, and the field named `mode`. | Three octal digits with an optional leading zero. |
| `retry.backoff.type` | One type, `exponential`, with `base` and `max`. | An enum of that one value. A second name would have to be invented to widen it. |

### Bounds the documentation implies and does not state

| Where | Reading taken |
| --- | --- |
| `strategy.fan_out`, `batch(n)` | The size starts at one. `batch(n)` is one container per batch of n items, and a batch of zero is a shard that can never be filled. The pattern also refuses the leading-zero spelling `batch(007)`. |
| `resources.cpu`, `resources.memory` | Above zero, in both documents. A CPU allowance of zero is how a container is given no limit at all, and a memory ceiling of zero would stop the container before it started. This matches `pids`, `max_parallel` and `retain.fetches`, each of which the documentation bounds away from zero by what it says the value is for. |
| `include`, `secrets`, `step.needs`, `step.outputs` | At least one entry, and `secrets`, `needs` and `outputs` hold no duplicate. An empty list means exactly what omitting the key means, and a duplicated edge would concatenate one envelope twice. `mcp.tools` is deliberately left unbounded, because the documentation says an empty tool list serves a server with nothing on it and that this differs from declaring no block. |
| `mcpTool.timeout` | Bounded by the 120 second ceiling the documentation states, so `120s`, `2m` and `120000ms` are the longest forms the grammar accepts. The rule sits beside its companion, that an async tool carries no timeout, rather than being left to a validator that would have nothing to read but the literal in the file. |
| `include`, a path with a `ref` | Refused. A path include resolves inside the same commit, so it can never be stale and there is nothing for a ref to pin, which is the reasoning that also refuses a timeout on an async tool. |
| `step`, `workflow` beside the script keywords | Refused. `script` commands run inside `image` and `workflow` is an alternative to `image`, so a sub-workflow call has no container for a script, a shell, a `before_script` or an `after_script` to run in. |

### Named by the documentation, not placed by it

| Name | What is missing | Reading taken |
| --- | --- | --- |
| `grace` | The step keyword table names a grace period on the `timeout` row, between SIGTERM and SIGKILL, and places it in runner policy: no keyword in the file sets it. | No keyword is declared, and none is left to declare. The value belongs to the runner rather than to the workflow. Recorded as a `$comment` on `workflow.$defs/timeout`. |
| A sync webhook response | `response: sync` "returns a named workflow output", and no key names which output. | The enum stays bare. A workflow cannot yet write what the sentence describes, and a companion key would be one this release made up. Recorded as a `$comment` on `webhookTrigger.response`. |
| An exit code in a manifest | The exit code table reserves 121 to 124 for the runner and says a brick exiting with one has failed the contract whatever its manifest says, and no manifest property carries a code. | No definition is published, and no keyword either: a manifest has nothing to say about an exit code. The range is 0 success, 1 to 99 application failure, 100 to 119 transient, 120 invalid input, 121 to 124 reserved for the runner, 125 and above reserved for the runtime; it is kept here rather than as a `$defs` entry nothing refers to, because the language reference is a projection of these documents and would otherwise teach a manifest key that does not exist. |
| A brick's secret name meeting a workflow's | The manifest names what it needs and "the workflow decides which secret of its own namespace answers that name", and no keyword expresses that mapping. | Both names are written on one grammar, so that a manifest cannot require a name no workflow is able to write. The mount path `/agk/secrets/<name>` is the only link the two documents draw, and they now spell it the same way. |
| `run_id`, in the envelope | A run "carries a ULID", which is twenty-six Crockford base32 characters, while the run identifiers the documentation prints are not all of that length: twenty-six in the envelope, fifteen and twelve in the task message. | No length is imposed. A twenty-six character pattern would refuse the documentation's own task message examples. Recorded as a `$comment` on `envelope.meta.run_id`. |

### Shapes the schemas allow that the documentation does not show

| Where | Reading taken |
| --- | --- |
| `on` | Three of the seven kinds of trigger. `manual` is started at the API with its inputs supplied there, `mcp` is declared in the `mcp` block, and `terraform` and `workflow` are the caller's to make, so none of the four is written in this file. The documentation's own `on` block shows exactly these three. Recorded as a `$comment` on the block. |
| Hidden blocks | Accepted at the root of the entry point and under `steps`. The documentation shows them at the root of an included file only, and it defines a hidden block as a name starting with a dot that is never executed, which is true in either place. |
| `steps` | Not required at the root. The documentation lists no required keys beyond what a reader needs to know which document it is holding, and a file declaring inputs and a published surface with its graph in an include is a file this cannot refuse without a rule to refuse it by. |
| `defaults` | Sixteen keys where the documentation's example writes six. A default is defined as what a step inherits where it states nothing of its own, so every step keyword that is a setting rather than graph shape belongs here; `image`, `script`, `needs`, `inputs`, `outputs`, `params`, `if`, `merge`, `strategy`, `extends` and `workflow` say what the step is and what it depends on, and are refused. |
| `brick.runtime.user` | The refusal of root reads the uid half, so `nobody:0` is accepted. The documentation states the rule as a non-root user and justifies it by a process running as uid 0, and says nothing about the group. Recorded as a `$comment` beside the pattern. |
| `envelope.item` | `id`, `data` and `files` are all required. The documentation writes every item with all three and says an item with nothing attached carries an empty list, so absent is never the same as empty here. |

### Identity and access

The access shapes sit in `wire.schema.json` rather than in a document of their own because they are written on the wire's names: a login is a namespace name, a quota lists runner pools by the pool's name, and a maximum run duration is a timeout. A `$ref` may not leave a document here, so a separate document would have held a copy of each, and a copy is what drifts. Where one string holds a name, a group or a service account reference, the copy cannot be avoided and `COMPOSED_GRAMMAR` holds it to the original.

| Where | What the documentation gives | Reading taken |
| --- | --- | --- |
| `principalRef` | Grants written `group:team-ops` and `group:finance-leads`; the settled decisions add the login and `NS/NAME` for a service account. | One string, `oneOf` the three forms. A login holds neither a colon nor a slash, so the forms never overlap. `operator` is refused as a login and accepted only by `actor`, on the rows the v0.2.5 token wrote. |
| `group.name`, `serviceAccount.name` | Names spelled `team-finance`, `finance-leads`, `agentiik`, and no grammar. | The namespace grammar and its reserved words, by `$ref`. Inside a reference only the grammar is checked: a reserved word never names a namespace, so a reference through one names nothing and the API refuses it for that. |
| `group.members` | "Named set of users". | Logins only. A group inside a group would turn effective permissions into a graph walk. |
| `accessGrant` | "Principal, role, optional expiry, optional deny", and a deny drawn as `deny alice → run:read_data`. | Exactly one of `role` and `deny`, and `deny` names one permission, since no role is `run:read_data` alone. Named `accessGrant` because `$defs/grant` is already a task's bearer token. |
| `accessGrant.scope`, `apiToken.scope.within` | A Terraform scope holding a workflow's identifier, `finance/monthly-invoicing`, and a namespace imported as `finance`. | A string, the namespace or `NS/NAME` with the workflow half on the identifier grammar the workflow file writes. |
| `apiToken.scope` | "An optional scope that can only narrow its principal's rights", and nothing on its shape. | `permissions` and `within`, each optional, at least one present; the rights are the principal's intersected with both. |
| `apiToken.expires_at` | 90 days by default, at most a year. | Required. The two bounds are relative to `created_at` and left to the API, pinned by a validator fixture. |
| `passkey.kind` | A table printing `synced` and `device-bound`, recorded from the BE and BS flags. | Spelled as printed, and held to `backup_eligible`: set means `synced`. `backup_state` cannot be set without it. |
| `principal`, `credential` | Kinds printed "user", "group", "service account". | Discriminated by `kind` for a principal (`service_account`, with an underscore like every multi-word value here) and by `type` for a credential, since a passkey already has a `kind`. |
| `user.admin`, `user.suspended` | An administrator created with `--admin`; an account that has not enrolled "suspended". | Two booleans, false by default. |
| `namespaceRecord.quotas` | The quota table lists six, `allowed_runner_pools` among them; the Terraform example writes it beside the `quotas` block. | Inside `quotas`, as the table has it. The provider is free to spell its HCL either way; this is the API's record. |
| `quotas.*` | The six names and what each bounds. | Every quota optional, absent setting no bound of the namespace's own. The four counts start at one. `max_run_duration` refers to the task message's timeout grammar. `allowed_runner_pools` refers to the pool's name and refuses an empty list, because a pool's own empty list of namespaces means every one. |
| `namespaceRecord.auth_policy` | "A namespace may tighten it, never loosen it". | The same shape as the installation's, each key absent inheriting the installation's value. Whether it tightens needs the installation's policy and is left to the API. |
| `authPolicy.min_passkeys` | "integer, default 2". | At least one: zero would let a password go from an account with nothing to replace it. |

### The API's routes

The documentation's table names each route and what it does, and settles few of the shapes a client needs. Where it is silent, `openapi.json` took these readings, each written as a description in the document too.

| Where | What the documentation gives | Reading taken |
| --- | --- | --- |
| `DELETE /api/v1/me/credentials` | "GET, DELETE /api/v1/me/credentials", with no path segment for the one credential removed. | The credential is named by a required `id` query parameter, keeping the route as the table writes it. A path segment, as tokens and grants have, would be a route the table does not list. |
| Every body | The Request bodies table caps the runner's bodies, a run and a push, and lists none of these. | 64 KiB, the cap of the other small bodies, and closed to fields the route does not read, save Web Authentication's own objects, which the browser extends. |
| Statuses | None, for these routes. | 400 for a body refused as Request bodies says or a value outside its grammar. 401 for no credential or one not accepted, and for every failed sign-in, one sentence for every reason. 403 at installation scope, for an enrolment-only session, for a scoped token minting another, and where a policy setting forbids the credential offered. 404 at namespace and workflow scope for the absent and the hidden alike, as the API already answers. 409 for a name already held and a change the rules forbid. 422 for a body naming what does not exist or is not the caller's, or an expiry out of bounds. 201 for what is created, 204 for a removal, 200 otherwise. |
| An administrator's route naming a namespace | "PUT is an administrator's", on a namespace's policy and quotas. | 403 before the namespace is looked up, so that a refusal says nothing of whether it exists. |
| `POST /api/v1/auth/passkey/options`, `/verify` | Options carrying the challenge, the Relying Party Identifier and the user verification; a verification that records the flags and opens a session. | Asked for by `{ceremony}`. The options are Web Authentication Level 3's `PublicKeyCredentialCreationOptionsJSON` and `PublicKeyCredentialRequestOptionsJSON`, and the credential is the `RegistrationResponseJSON` or `AuthenticationResponseJSON` the browser's `toJSON()` gives, spelled as the Recommendation spells them. A sign-in asks for a discoverable passkey, `allowCredentials` empty, so no login is sent before the ceremony. |
| An enrolment link's code | Carried after `#`, which reaches no access log. | The enrolment page sends it as `code` with the registration options; it is held against the challenge and consumed by the verification, so a ceremony dismissed halfway does not burn it. A recovery code is the same kind of code. |
| `agk login` | The page is handed "the loopback address and the verifier's SHA-256" and redirects "with a one-time code". | The page takes `redirect_uri` and `code_challenge`, the names RFC 6749 and RFC 7636 give them, and passes them on as `terminal` with the sign-in; the answer's `redirect_to` is the whole address, written by the API. The loopback is `127.0.0.1` or `[::1]`, never a name, as RFC 8252 advises. The exchange takes `{code, code_verifier, device_label}` and answers 201 with the token. A password sign-in carries `terminal` too, which is how `agk login` works on an installation addressed by an IP address. |
| Credential values | 256 bits, stored hashed, shown once; the wire's `agkjoin_`, `agkrunner_` and `agkgrant_`. | `agktoken_` for an API token, `agkenrol_` for an enrolment or a recovery code, `agkcode_` for `agk login`'s code, each followed by at least 43 base64url characters. |
| The session cookie | An opaque identifier in a cookie, `HttpOnly`, `Secure`, `SameSite=Lax`. | Named `__Host-agentiik_session`, which a browser refuses unless it is `Secure`, set for the whole origin and bound to no domain. |
| An enrolment-only session | It "can enrol passkeys and nothing else". | It reaches the registration ceremony, and every other route answers it 403. |
| Lists | `GET /api/v1/{ns}/secrets` answers `{"secrets": [...]}`. | Every list is an object with one plural key: `credentials`, `tokens`, `namespaces`, `users`, `groups`, `service_accounts`, `grants`. An expired grant and a token no longer accepted are left out. |
| `GET /api/v1/auth/policy`, `/{ns}/auth/policy`, `/namespaces/{ns}/quotas` | Who may read them is not said. | The installation's policy, any authenticated principal, every setting written out. A namespace's policy and quotas, an administrator and anyone holding a grant in the namespace; its policy answers only the settings it sets, so that what `PUT` wrote reads back. |
| `PUT` on a policy or quotas | "PUT is an administrator's". | The body is the whole: a setting left out returns to its default, a quota left out sets no bound. |
| `POST /api/v1/users`, asked again | The first administrator may be created again "for a fresh link until they have enrolled". | 200 with a fresh link for the same login, display name and `admin`, the link before revoked; 409 for any other difference or once the user has enrolled. |
| Reading grants | Who may list them is not said. | `grant:manage` at the scope, since the list names everyone who holds access. |
| A token minting a token | A scope "can only narrow its principal's rights". | A token narrowed by a scope cannot mint another, which would escape the narrowing. |
| `GET /api/v1/me` | "Identity, group memberships, effective permissions per namespace, and notifications". | `permissions` keyed by scope: a namespace's key, and a workflow's `NS/NAME` where a grant or a deny on it changes that, narrowed by the presenting token's scope. `admin` says whether the caller administers, the bootstrap token included. One notification kind, `admin_access_widened`, carrying the grant; no route marks one read yet. |
| `POST /api/v1/service-accounts` | "A new one in one of them, written NS/NAME". | `{namespace, name}`, the record's own shape, `agentiik` refused by the grammar. |
| `PUT`, `DELETE /api/v1/groups/{group}/members/{login}` | "Adds or removes one member, touching no grant". | No body, and the group answered either way; adding a member already there or removing one who is not changes nothing. |

## Fixtures

Each group under `fixtures/` holds `valid/` and `invalid/` documents, and
[`fixtures/index.json`](fixtures/index.json) records what every one of them pins: what a
valid fixture covers, and for an invalid one, the rule it breaks and where the
documentation states it. A fixture the index does not list fails the build, because a
fixture nobody documented proves nothing.

An invalid fixture says what refuses it. `schema` means this document alone refuses it,
and a consumer can assert that with a validator and nothing else. `validator` means the
documentation states the rule but JSON Schema cannot express it, because it needs the
graph, a brick manifest, an included file or the expression language. Those fixtures are
schema valid on purpose, and the build asserts that too: the day one of them starts being
refused here, either the schema reached past what it can know or the index is wrong.

## Licence

Apache-2.0, see [LICENSE](LICENSE). Permissive on purpose: everything here ends up inside
somebody else's brick or client, and copyleft would reach into work that has nothing to
do with the engine. [LICENSING.md](https://github.com/agentiik/.github/blob/main/LICENSING.md) has the reasoning.

## Contributing

[CONTRIBUTING.md](https://github.com/agentiik/.github/blob/main/CONTRIBUTING.md), under the Developer Certificate of Origin 1.1.
