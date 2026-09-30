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
| [`workflow.schema.json`](workflow.schema.json) | `https://schemas.agentiik.dev/workflow.schema.json` | `agentiik.yaml`, the entry point of a workflow repository: `apiVersion`, `kind`, `metadata`, `inputs`, `outputs`, `on`, `mcp`, `include`, `vars`, `secrets`, `defaults`, `concurrency`, `timeout` and `steps`, with every step keyword; and, as `#/$defs/fragment`, an included file. |
| [`brick.schema.json`](brick.schema.json) | `https://schemas.agentiik.dev/brick.schema.json` | `/agk/brick.yaml`, the manifest an image carries to become a brick: its ports, its parameters, the secrets it expects and what it needs from the container it is given. |
| [`envelope.schema.json`](envelope.schema.json) | `https://schemas.agentiik.dev/envelope.schema.json` | `{ meta, items }`, the one document that travels along a port. |
| [`wire.schema.json`](wire.schema.json) | `https://schemas.agentiik.dev/wire.schema.json` | Every message between the controller, the bus, the runner and the API: the task message, the progress of the task and its result, a runner's registration, its heartbeat, the rotation of its credential, the redemption of a task's grant, a log shipment, and a runner pool with the token issued from it. Beside them, the identity and access records the API keeps: a principal and the one string that names it, a credential, an API token without its value, a grant, the roles and the permissions, a namespace with its quotas, the authentication policy, and a notification told to a principal in `/me`. And the workflow repository's: a repository, one of its refs, a version, and the graph a version resolves to. |
| [`openapi.json`](openapi.json) | `https://schemas.agentiik.dev/openapi.json` | The routes of `/api/v1`, so far those of v0.3.0's access: signing in with a passkey or a password and signing out, the sign-in page and its files, a password and a TOTP generator set, `agk login`'s exchange, the authentication policy, `/me` with the caller's credentials and notifications, users and their enrolment, groups and their members, service accounts, namespaces and their quotas, grants at namespace and workflow scope, and API tokens; and v0.4.0's workflow repositories, created, read, renamed, moved, protected and deleted, the tree at a ref, and the image pins and brick manifests a push is judged against. OpenAPI 3.1, whose schemas are JSON Schema 2020-12. |

`wire.schema.json` is a family rather than one document's shape: a reader validates against the member it is holding, `#/$defs/taskMessage` or `#/$defs/taskResult` and so on. They sit in one document because they share a vocabulary, the run and task states and the identifiers being the same strings everywhere, and because a `$ref` may not leave a document here: an enumeration written twice is an enumeration that drifts. The fixture index names one group per member for the same reason, so a fixture pins one message rather than something the wire allows somewhere.

`openapi.json` is the one document whose `$ref` leaves it, and only for a schema beside it: a user is `wire.schema.json#/$defs/user`, resolved relative to the document as every OpenAPI consumer resolves a reference. The wire is where the access records are defined, and a copy of them here would be the drift the rest of this repository refuses. What the document defines itself is what only a route carries: a request body, a list, a token shown once, and Web Authentication's own JSON forms. A generator reads the two files side by side, or a bundler inlines the wire's definitions first. It describes the routes the documentation's table lists at [#api](https://agentiik.github.io/docs#api), and the build holds the two to each other.

Beside them, [`fixtures/`](fixtures) holds the documents that pin what the schemas accept
and what they refuse, and [`tools/check.py`](tools/check.py) is the check the build runs.

[`language/`](language) is the language reference, generated from `workflow.schema.json` by [`tools/language.py`](tools/language.py) and never edited by hand. It is what `workflow.language` answers with, and the pages the site renders: see [The language reference](#the-language-reference).

## Running the check

```sh
python -m pip install -r requirements.txt
python tools/check.py
```

No arguments, from anywhere in the repository. It is the same command [`.github/workflows/validate.yml`](.github/workflows/validate.yml) runs, so a green run locally means a green run there. Add `-v` to have it name every fixture and say why each refused one was refused.

The route check reads the documentation of main from <https://agentiik.github.io/docs/v/main/>, because this repository's main follows it. Where the two change together, or offline, point it at a checkout instead: `python tools/check.py --docs ../agentiik.github.io`. The documentation's pull request merges first, since it is the authority, and this repository's build is green against the site from then on.

Eleven things fail the build:

1. a schema that is not a legal JSON Schema 2020-12 document, that does not carry the
   `$id` it is published under, or that holds a `$ref` leading nowhere;
2. a keyword without a `description` or without `examples`;
3. an example that does not validate against the keyword it illustrates;
4. a fixture that does not behave as `fixtures/index.json` says it does, a repository case among them;
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
   and a parameter name, are listed in `ONE_GRAMMAR` in `tools/check.py` with every place each is written. A grammar written inside a longer pattern, the namespace name inside `group:team-finance` or `finance/agentiik`, is listed in `COMPOSED_GRAMMAR` with the template it is written into, and has to read exactly as that template filled in. The bound on a namespace's name is held the same way: its `maxLength` in both documents by `ONE_GRAMMAR`, and the `not` that bounds the name inside a reference by `BOUNDED_NAME`; so are the 255 characters of a name the workflow file writes, in every document that carries one, each half of a reference by `BOUNDED_PATH`, and the 250 of a port in the workflow file and the manifest, the wire and the envelope taking a port up to 255 as the engine sends one until v0.4.0;
7. an em dash, anywhere in any text file;
8. an `openapi.json` a generator cannot rely on: not OpenAPI 3.1, a field a reader needs missing, a path parameter declared and not in its path or the other way round, an `operationId` used twice, a status that is not one, a schema the 2020-12 metaschema refuses or one writing `nullable` or `example`, which 2020-12 ignores, or a `$ref` leading nowhere, inside it or into a schema beside it;
9. an operation, a parameter, a request body, a response, a header or a schema keyword of it without a description or without examples, or an example that does not validate against what it illustrates, a reference into the wire resolved as a consumer resolves it;
10. a route the documentation's table lists and `openapi.json` does not describe, or the other way round, or an operation whose `externalDocs` points at an anchor the page does not carry. A route deliberately not described yet is named in `NOT_DESCRIBED_YET` in `tools/check.py` with the reason, and the list is held exact: a route on it that is now described, or gone from the table, fails too. A read of the page that comes back partial, no page, no `#api` section, no table or a row that cannot be read, fails rather than agreeing with nothing;
11. a `language/` that is not exactly what `tools/language.py` generates from the schemas, a keyword of `workflow.schema.json` that no topic covers, a topic with no worked example, or a worked example that, read back from the YAML its page shows with a YAML 1.2 loader, is not the example it illustrates or does not validate against the keyword that carries it.

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

The API is held to the same rule for the same reason: the API reference is generated from `openapi.json`, and the console, `agk` and the Terraform provider read it as their one description of the API, so an operation or a field without a description is one none of them can explain.

## The language reference

`workflow.language`, the MCP tool, teaches the language one topic at a time, and the documentation names the topics: "repository, inputs, outputs, triggers, steps, ports, needs, merge, fan_out, retry, expressions, secrets, files, script, includes, mcp". Without a topic it answers an orientation. Both are generated here, so the tool, the command line and the site teach one language, the one the validator enforces:

```sh
python tools/language.py
```

It writes three kinds of file under `language/`:

| File | Holds |
| --- | --- |
| `index.md` | The orientation: what the language is, one complete minimal workflow, the topics, and the schema parts by name. |
| `<topic>.md` | One page per topic: a summary, the keywords it covers, the schema fragment governing them and worked examples, each written where it goes in `agentiik.yaml`. |
| `topics.json` | The same for a program: each topic's `name`, `page`, `summary`, the `keywords` it covers as pointers into `workflow.schema.json`, and the `paths` it answers for; and the `parts`, each a `name`, the `file` and `$id` it is published as, and its `title` and `summary`. |

Every sentence on a page is a `description` of the schema, and every example an entry of an `examples` array. What `tools/language.py` adds is structure alone: which keyword belongs to which topic, set by `TOPICS`, and the order a page is read in. A topic's summary is the description of one keyword it names, its anchor. A keyword belongs to the topic whose place is the longest prefix of where it is declared, so the steps topic covers the step while the retry topic takes the step's `retry` away from it, and the build fails on a keyword no topic covers. The orientation's minimal workflow is the first example of the schema's root, which is why that example is the smallest workflow that runs: one step, no brick to pull, one output.

A path in `topics.json` is a JSON Pointer to where a keyword is written in `agentiik.yaml` or an included file, in which `*` stands for any one name or index and `.*` for any one name starting with a dot, a hidden block's. It is the pointer a validation error names, so an error can name the topic that explains it: the topic of the longest pattern that matches, token by token, the error's pointer or the start of it. A place is claimed by the keyword written there and so by one topic, which the build holds: a definition claims none, since the property it is reached through answers for it, and neither does a keyword of the included file, which restates one of the entry point's at the same place.

A part is named after its file, so `workflow`, `brick` and `envelope` are `workflow.schema.json`, `brick.schema.json` and `envelope.schema.json`, published under the `$id` each carries. `workflow.schema` and `agentiik://schema/{part}` take one of these names.

A definition written at several places, an expression or a duration, shows its examples as values rather than placed at the first of those places, where an expression would read as an event filter. A keyword written at one place is shown there, with the names its keyword's `propertyNames` examples give: a step is called `normalize` because that is the first example of a step's name.

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
| `workflow.$defs/identifier` | Names spelled `monthly-invoicing`, `finance`, `create_invoice`, `orders`, `out`, `rejected`, and the rule that a name travels through a URL, an environment variable and a tool list unchanged. | Letters, digits, hyphens and underscores, first character alphanumeric. It is the grammar every name in the file is keyed on, and `brick.$defs/portName` is the same one so that a port declared in a manifest can be named in a workflow. At most 255 characters, and a port or a workflow output 250 as `$defs/portName`, the bounds the documentation's grammar table states, held by `ONE_GRAMMAR` in every copy of the grammar, the wire and the envelope taking a port up to 255 as the engine sends one until v0.4.0; a hidden block's name, never a directory, is left unbounded. |
| `workflow.metadata.name` | A workflow name forms the `<namespace>/<name>` identity. Every workflow and namespace it writes is lowercase and hyphenated, and it gives a narrower rule only for a published brick name, which the catalog files a page under. | The identifier grammar, not the brick's. A rule written about a catalog entry is not evidence about a git remote, so the narrower reading would be borrowed rather than read. Recorded as a `$comment` on both names. |
| `workflow.$defs/duration` | Durations written `2s`, `30s`, `10m`, `24h`, `7d`, and a brick parameter pattern in the manifest example spelling `^[0-9]+(ms\|s\|m)$`. | A number and one of `ms`, `s`, `m`, `h`, `d`. The set is assembled from what is written; no other unit appears anywhere. |
| `workflow.$defs/expression` | A CEL expression inside `${{ }}`, and the roots it may read. | An unconstrained string. Which roots exist, and where `item` and `secrets` may be read, is expression-language work rather than shape, so those rules sit with the validator and the fixtures under `refused_by: validator` pin them. |
| `scheduleTrigger.cron` | A five-field cron expression read in the timezone beside it. | Five non-space fields, and nothing about what a field may hold. Refusing a field the documentation never describes would be inventing a dialect. |
| `webhookTrigger.method` | One method, `POST`. | Upper-case letters. An enum would fix a set the documentation never gives. |
| `runsOn` items, `egress.allow` items | Selectors written `zone=dmz`, `arch=amd64`; destinations written `api.billing.example.com:443`. | `key=value` and `host:port`. The port is bounded to 1 through 65535, because the proxy opens a connection to it and there is nothing above that to open. |
| `files[].mode` | One value, `"0444"`, and the field named `mode`. | Three octal digits with an optional leading zero. |
| `files` globs | "A path or glob relative to the root", written `./sql/**`, and a long form that relocates "a path". | `*` inside one segment, `?` one character, `[abc]` a set or a range, `**` as a segment of its own zero or more whole segments, so `./sql/**` is every file at any depth under `sql/`. A path names a file or a directory with everything under it. A directory or a glob relocated with `to` keeps each file's path below it, or below the glob's segments before its first wildcard, and `to` is absolute, as the task message and the runner already hold it. |
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
| An included file | "A fragment: hidden blocks and shared settings, no `apiVersion`, `kind` or `metadata`", and validating one against the workflow schema "a category error". | `$defs/fragment`, apart from the root: hidden blocks, `steps`, `defaults`, `vars`, `secrets` and `include`, and none of `inputs`, `outputs`, `on`, `mcp`, `concurrency` and `timeout`, the workflow's boundary, which the engine's reader refuses there too. Its path includes resolve against its own directory, as the engine resolves them. |
| Hidden blocks | Accepted at the root of the entry point and under `steps`. The documentation shows them at the root of an included file only, and it defines a hidden block as a name starting with a dot that is never executed, which is true in either place. |
| `steps` | Not required at the root. The documentation lists no required keys beyond what a reader needs to know which document it is holding, and a file declaring inputs and a published surface with its graph in an include is a file this cannot refuse without a rule to refuse it by. |
| `defaults` | Sixteen keys where the documentation's example writes six. A default is defined as what a step inherits where it states nothing of its own, so every step keyword that is a setting rather than graph shape belongs here; `image`, `script`, `needs`, `inputs`, `outputs`, `params`, `if`, `merge`, `strategy`, `extends` and `workflow` say what the step is and what it depends on, and are refused. |
| `brick.runtime.user` | The refusal of root reads the uid half, so `nobody:0` is accepted. The documentation states the rule as a non-root user and justifies it by a process running as uid 0, and says nothing about the group. Recorded as a `$comment` beside the pattern. |
| `envelope.item` | `id`, `data` and `files` are all required. The documentation writes every item with all three and says an item with nothing attached carries an empty list, so absent is never the same as empty here. |

### Identity and access

The access shapes sit in `wire.schema.json` rather than in a document of their own because they are written on the wire's names: a login is a namespace name, a quota lists runner pools by the pool's name, and a maximum run duration is a timeout. A `$ref` may not leave a document here, so a separate document would have held a copy of each, and a copy is what drifts. Where one string holds a name, a group or a service account reference, the copy cannot be avoided and `COMPOSED_GRAMMAR` holds it to the original.

| Where | What the documentation gives | Reading taken |
| --- | --- | --- |
| `principalRef` | Grants written `group:team-ops` and `group:finance-leads`; the settled decisions add the login and `NS/NAME` for a service account, and name `operator` and `installation` as authors of rows. | One string, `oneOf` the three forms. A login holds neither a colon nor a slash, so the forms never overlap. `operator` and `installation` are refused as logins. `actor` accepts both: `operator` on the rows the v0.2.5 token and the bootstrap token wrote, and `installation` on the owner grant a user's personal namespace is created with at their first sign-in, which `accessGrant.granted_by` carries. |
| `group.name`, `serviceAccount.name` | Names spelled `team-finance`, `finance-leads`, `agentiik`, and no grammar. | The namespace grammar and its reserved words, by `$ref`. Inside a reference only the grammar is checked: a reserved word never names a namespace, so a reference through one names nothing and the API refuses it for that. |
| `namespace`, and the `login`, `group.name` and `serviceAccount.name` written on it | Each at most 255 characters, the most a directory or a bus subject token holds a name to. | `maxLength` 255 on `$defs/namespace`, which the others reach by `$ref`. Inside `groupRef`, `serviceAccountRef` and a workflow's `grantScope`, where a name sits beside a prefix or another name and a `maxLength` would bound the whole string, a `not` refuses one character past the bound. |
| The reserved words, `stats` among them | `stats` is refused at creation from v0.3.0, for v0.6.0's `GET /api/v1/stats/pools`, and a namespace made before v0.3.0 under it is still served, every route of it, with nothing to do. | `stats` joins the words `$defs/namespace` refuses. A pattern cannot tell a namespace created before v0.3.0 from one asked for now, so a reader validating what such an installation answers meets a refusal the API does not make; the description says so. |
| `group.members` | "Named set of users". | Logins only. A group inside a group would turn effective permissions into a graph walk. |
| `accessGrant` | "Principal, role, optional expiry, optional deny", and a deny drawn as `deny alice → run:read_data`. | Exactly one of `role` and `deny`, and `deny` names one permission, since no role is `run:read_data` alone. Named `accessGrant` because `$defs/grant` is already a task's bearer token. |
| `accessGrant.scope`, `apiToken.scope.within` | A Terraform scope holding a workflow's identifier, `finance/monthly-invoicing`, and a namespace imported as `finance`. | A string, the namespace or `NS/NAME` with the workflow half on the identifier grammar the workflow file writes. |
| `apiToken.scope` | "An optional scope that can only narrow its principal's rights", and nothing on its shape. | `permissions` and `within`, each optional, at least one present; the rights are the principal's intersected with both. |
| `apiToken.expires_at` | 90 days by default, at most a year. | Required. The two bounds are relative to `created_at` and left to the API, pinned by a validator fixture. |
| `passkey.kind` | A table printing `synced` and `device-bound`, recorded from the BE and BS flags. | Spelled as printed, and held to `backup_eligible`: set means `synced`. `backup_state` cannot be set without it. |
| `principal`, `credential` | Kinds printed "user", "group", "service account". | Discriminated by `kind` for a principal (`service_account`, with an underscore like every multi-word value here) and by `type` for a credential, since a passkey already has a `kind`. |
| `user.admin`, `user.suspended` | An administrator created with `--admin`; an account that has not enrolled "suspended". | Two booleans, false by default. |
| `user.last_sign_in_at` | One user answered with when they "last signed in". | Optional, absent until the first sign-in. |
| `user.suspended_for` | One user answered with `suspended_for`, `no_passkey`, "where the policy suspended them". | `no_passkey`, the one reason the policy writes, and only beside `suspended: true`, as the table holds it. Absent for a suspension the policy did not make, which no enrolment lifts. |
| `namespaceRecord.quotas` | The quota table lists six, `allowed_runner_pools` among them; the Terraform example writes it beside the `quotas` block. | Inside `quotas`, as the table has it. The provider is free to spell its HCL either way; this is the API's record. |
| `quotas.*` | The six names, what each bounds, and that `max_concurrent_tasks` and `max_retention_days` always hold a value. | Every quota optional in the shape, which is both what a write sends and what the API answers: that the two always hold a value is the API's to keep, and every record the examples answer shows them. The other four, absent, set no bound of the namespace's own. The four counts start at one. `max_run_duration` refers to the task message's timeout grammar. `allowed_runner_pools` refers to the pool's name and refuses an empty list, because a pool's own empty list of namespaces means every one. |
| `namespaceRecord.auth_policy` | "A namespace may tighten it, never loosen it". | The same shape as the installation's, each key absent inheriting the installation's value. Whether it tightens needs the installation's policy and is left to the API. |
| `authPolicy.min_passkeys` | "integer, default 2". | At least one: zero would let a password go from an account with nothing to replace it. |
| `notification` | Three things told in `GET /api/v1/me`, named `admin_access_widened`, `passkey_counter_refused` and `break_glass_recovery`: an administrator writing a grant by the installation's power, putting a user in a group holding a role, or widening their own access, told to the namespace's owners and, where it had nobody to tell before, the other administrators as well; a sign-in refused for a passkey's signature counter, told to its user; and a recovery code `agentiik-api recover` issued an administrator, told to every administrator. Each kept 90 days or until dismissed. | A record of the wire rather than of `openapi.json`, since the API keeps it and a route dismisses it by its identifier. Told apart by `kind`: `admin_access_widened` carries `namespace` and `grant`, the grant or deny as it was written, `act`, which of five acts widened access, and `by`, who did it, a login or `operator`, since the grant's own `granted_by` may be somebody else long before, and `login` on `joined_group` alone, the user put in; `passkey_counter_refused` the passkey's `credential` ID, `break_glass_recovery` the recovered administrator's `login`, and each refuses the others' fields. |

### The workflow repository

| Where | What the documentation gives | Reading taken |
| --- | --- | --- |
| `resolvedGraph` | "The resolved graph, not the file's text: includes resolved, inheritance applied, ports named as the manifests declare them", recorded per version. | What the engine's resolution gives: every step with its keywords resolved, a keyword absent where resolution leaves the language's default and written otherwise, save `idempotent` and, on a script step, `shell`, which are always written; `before_script`, `after_script` and `shell` on a script step alone, although the engine's resolved step carries them wherever a layer writes them, since a brick runs its own entry point and a call runs no container; images by digest, a brick step's manifest `name` and `version`, `needs` and `files` in their long forms, `extends` as the chain of blocks, the includes read with the commit each workflow include resolved to, and the steps' order. No namespace: a rename or a move changes the repository's, never what a commit resolves to. Expressions are kept as written, and the blocks the engine passes through, `on` and `mcp`, are held to `workflow.schema.json` rather than copied into the wire. |
| `ref.name`, `repository.default_branch` | A ref table of name, commit, protection, who moved it and when; a default branch. | A ref in full, `refs/heads/` or `refs/tags/`, so that a branch and a tag of one name are two refs; a default branch by its short name, as HEAD names it. Both on git's own rules for a ref name, held together by `ONE_GRAMMAR` and `COMPOSED_GRAMMAR`. |
| `version.author` | "Author, timestamp" per version. | The principal who pushed it, who answers for what it names, secrets included; the git author is the history's, `historyEntry.author`. |

### The API's routes

The documentation's table names each route and what it does, and settles few of the shapes a client needs. Where it is silent, `openapi.json` took these readings, each written as a description in the document too.

| Where | What the documentation gives | Reading taken |
| --- | --- | --- |
| Every body | The Request bodies table caps the runner's bodies, a run and a push, and lists none of these. | 64 KiB, the cap of the other small bodies, save a recording of image pins and brick manifests, which the documentation gives 8 MiB since it carries manifests whole; and closed to fields the route does not read, save Web Authentication's own objects, which the browser extends. |
| Statuses | None, for these routes. | 400 for a body refused as Request bodies says or a value outside its grammar. 401 for no credential or one not accepted, and for every failed sign-in, one sentence for every reason. 400 as well for two credentials, a bearer token beside the session cookie or two session cookies, and for a body sent to a route that reads none. 403 at installation scope, for a session that may only enrol, for a scoped token minting another, where a policy setting forbids the credential offered, for a request changing something that a session carries from another origin, and for a credential that lasts asked from a session signed in to longer ago than 10 minutes, the last with RFC 9470's challenge in `WWW-Authenticate`. 429 with `Retry-After` past the password counts, and 503 where no turn to hash a password comes within five seconds. 404 at namespace and workflow scope for the absent and the hidden alike, as the API already answers. 409 for a name already held and a change the rules forbid. 422 for a body naming what does not exist or is not the caller's, or an expiry out of bounds. 201 for what is created, 204 for a removal, 200 otherwise. |
| An administrator's route naming a namespace | "PUT is an administrator's", on a namespace's policy and quotas, and `DELETE /api/v1/namespaces/{ns}` is "Administrator only". | 403 before the namespace is looked up, so that a refusal says nothing of whether it exists. |
| `POST /api/v1/auth/passkey/options`, `/verify` | Options carrying the challenge, the Relying Party Identifier and the user verification; a verification that records the flags and opens a session. | Asked for by `{ceremony}`. The options are Web Authentication Level 3's `PublicKeyCredentialCreationOptionsJSON` and `PublicKeyCredentialRequestOptionsJSON`, and the credential is the `RegistrationResponseJSON` or `AuthenticationResponseJSON` the browser's `toJSON()` gives, spelled as the Recommendation spells them. A sign-in asks for a discoverable passkey, `allowCredentials` empty, so no login is sent before the ceremony. |
| An enrolment link's code | Carried after `#`, which reaches no access log. | The enrolment page sends it as `code` with the registration options, or beside the password it sets at `POST /api/v1/auth/password/enrol`; it is held against the challenge and consumed by the verification, or spent by the password, so a ceremony dismissed halfway does not burn it. A recovery code is the same kind of code. |
| `agk login` | The page is handed "the loopback address and the verifier's SHA-256" and redirects "with a one-time code". | The page takes `redirect_uri` and `code_challenge`, the names RFC 6749 and RFC 7636 give them, and passes them on as `terminal` with the sign-in; the answer's `redirect_to` is the whole address, written by the API. The loopback is `127.0.0.1` or `[::1]`, never a name, as RFC 8252 advises. The exchange takes `{code, code_verifier, device_label}` and answers 201 with the token. A password sign-in carries `terminal` too, which is how `agk login` works on an installation addressed by an IP address. |
| Credential values | 256 bits, stored hashed, shown once; the wire's `agkjoin_`, `agkrunner_` and `agkgrant_`. | `agktoken_` for an API token, `agkenrol_` for an enrolment or a recovery code, `agkcode_` for `agk login`'s code, each followed by at least 43 base64url characters. |
| The session cookie | An opaque identifier in a cookie, `HttpOnly`, `Secure`, `SameSite=Lax`. | Named `__Host-agentiik_session`, which a browser refuses unless it is `Secure`, set for the whole origin and bound to no domain. |
| A session that may only enrol | It "enrols passkeys and sets its password, and nothing else". | It reaches the registration ceremony, `PUT /api/v1/me/password` and the sign-out, which read the session themselves, and every other route answers it 403. `sessionKind` writes it `enrolment`. |
| Lists | `GET /api/v1/{ns}/secrets` answers `{"secrets": [...]}`. | Every list is an object with one plural key: `credentials`, `tokens`, `namespaces`, `users`, `groups`, `service_accounts`, `grants`; a repository's images, two lists, are an object with two, `pins` and `manifests`. An expired grant and a token no longer accepted are left out. |
| `GET /api/v1/auth/policy`, `/{ns}/auth/policy`, `/namespaces/{ns}/quotas` | Who may read them is not said. | The installation's policy, any authenticated principal, every setting written out. A namespace's policy and quotas, an administrator and anyone holding a grant in the namespace; its policy answers only the settings it sets, so that what `PUT` wrote reads back. |
| `PUT` on a policy or quotas | "PUT is an administrator's". | The body is the whole: a setting left out returns to its default, and a quota left out sets no bound, save `max_concurrent_tasks` and `max_retention_days`, which keep their value as the documentation says. |
| `POST /api/v1/users`, asked again | The first administrator may be created again "for a fresh link until they have enrolled". | 200 with a fresh link for the same login, the link before revoked, a `display_name` or `admin` left out keeping what is recorded; 409 for one written otherwise than recorded, or once the user has enrolled. `userCreate` requires the login alone: a user created with no display name is given their login. |
| Reading grants | Who may list them is not said. | `grant:manage` at the scope, since the list names everyone who holds access. |
| A token minting a token | A scope "can only narrow its principal's rights". | A token narrowed by a scope cannot mint another, which would escape the narrowing. |
| `GET /api/v1/me` | "Identity, group memberships, effective permissions per namespace, and notifications". | `permissions` keyed by scope: a namespace's key, and a workflow's `NS/NAME` where a grant or a deny on it changes that, narrowed by the presenting token's scope, a workflow where the caller holds nothing left out as one it cannot read. `admin` says whether the caller administers, the bootstrap token included, and is false through a token whose scope takes the powers away. `notifications` are the wire's `notification`, newest first. |
| `DELETE /api/v1/me/notifications/{id}` | Dismisses one, and one not dismissed is kept 90 days. | 204; 404 for one dismissed already or past its 90 days, as for one that was never the caller's. |
| The password routes | A password set from an enrolment code, a password set, changed and removed from a session, with the current one to change it. | `{code, password}` at `POST /api/v1/auth/password/enrol`, `{password, current_password}` at `PUT /api/v1/me/password`, the names the page's forms write. `newPassword` holds the length rules as far as a schema can: `minLength` 12 counts code points as the API does, and `maxLength` 1,024 is the most characters 1,024 bytes hold, the byte count being the API's. |
| The TOTP routes | A generator's secret and its `otpauth://` URI answered once, and confirmed and removed with a code it shows. | `{id, secret, uri, expires_at}` at the start: the secret in base32 without padding, 32 characters for 160 bits, and the URI in Google's Key Uri Format with every parameter written, issuer `Agentiik`, account `LOGIN@HOST`. The confirmation and the removal take `{totp}`, six digits, as the sign-in's `totp` is written. |
| `GET /auth/assets/{name}` | The page's stylesheet and three scripts, "revalidated by their ETag". | Named in the path, `page.css`, `page.js`, `codec.js` and `qr.js`, answered with `Cache-Control: no-cache` and an `ETag`, and 304 for a matching `If-None-Match`; a name the page does not hold is the 404 every absence is. |
| `POST /api/v1/auth/sign-out` | Ends the session and clears the cookie, 204 either way. | No body, and the cookie cleared as `Max-Age=0` with the attributes it was set with. |
| `POST /api/v1/service-accounts` | "A new one in one of them, written NS/NAME". | `{namespace, name}`, the record's own shape, `agentiik` refused by the grammar. |
| Workflow routes | Five rows: create, read, the tree at a ref, and, from the settled decisions, rename, move, protection and deletion; the platform tool `workflow.create` mirrors the API. | Creating one takes `workflow:write` at namespace scope, as registering a version does, so that an editor creates the repository its first push needs. 404 at namespace and workflow scope for a permission not held, as the grants routes answer; 422 for a move to a namespace absent or not the caller's, and for a default branch naming no branch. A rename and a change of branch or protection answer 200 with the repository; a move answers 202 with `Location`, and a deletion 202, since the controller carries both out after the answer. |
| `GET /api/v1/{ns}/workflows/{name}` | "Default branch head, resolved graph at that commit, commit history." | `{repository, version, graph, history, next}`: the version a run naming no ref runs with its graph, and a page of first-parent history, `limit` commits, 50 by default and at most 500 as runs are listed, from `from` or the head, `next` naming where the following page starts. |
| `GET /api/v1/{ns}/workflows/{name}/tree/{ref}` | "The tree at a ref." | `{commit, entries}`, each entry the version manifest's `path`, `mode`, `size` and `sha256`; `?path=` answers one file's bytes. A ref is a branch or a tag, short or in full, or a whole commit that is a version, and a name held by both a branch and a tag is 400 rather than a guess: every tree answered is a version's, held to a version's rules. |
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

Under `fixtures/repository/`, a case is a directory rather than a document: one push of a workflow repository as the pre-receive hook judges it, holding the commit's tree, stand-ins for what the hook reads from the installation (the repository's image pins and brick manifests, the namespace's secret declarations, and the repositories a workflow include reads), and either `expected.json`, the resolved graph, or `refusal.json`, the rule and where. The index's `repositories` entry says what each file of a case is and gives `case.json`, `tree.json` and `refusal.json` as JSON Schemas, held to the first three checks as the schemas are. A symbolic link, a submodule and a name that is not UTF-8 are listed in `tree.json` with their mode rather than committed, since none of them survives being committed here as what it is.

## Licence

Apache-2.0, see [LICENSE](LICENSE). Permissive on purpose: everything here ends up inside
somebody else's brick or client, and copyleft would reach into work that has nothing to
do with the engine. [LICENSING.md](https://github.com/agentiik/.github/blob/main/LICENSING.md) has the reasoning.

## Contributing

[CONTRIBUTING.md](https://github.com/agentiik/.github/blob/main/CONTRIBUTING.md), under the Developer Certificate of Origin 1.1.
