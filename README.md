# schemas

The contract every other repository reads: JSON Schema 2020-12 documents for the
workflow file, the brick manifest and the envelope. The OpenAPI document of the API
belongs here too and arrives in a later release.

This repository is versioned and released on its own, and pinned by every repository
that consumes it: the core, the bricks, the console, the iOS application and the Android
application. A schema change is a release here first.

What the schemas are written against is the specification at
<https://agentiik.github.io/docs>. Where the documentation states a rule, the schema
states it; where it is silent, the schema takes the reading that cannot contradict it.

## What is in here

| Document | `$id` | Describes |
| --- | --- | --- |
| [`workflow.schema.json`](workflow.schema.json) | `https://schemas.agentiik.dev/workflow.schema.json` | `agentiik.yaml`, the entry point of a workflow repository: `apiVersion`, `kind`, `metadata`, `inputs`, `outputs`, `on`, `mcp`, `include`, `vars`, `secrets`, `defaults`, `concurrency`, `timeout` and `steps`, with every step keyword. |
| [`brick.schema.json`](brick.schema.json) | `https://schemas.agentiik.dev/brick.schema.json` | `/agk/brick.yaml`, the manifest an image carries to become a brick: its ports, its parameters, the secrets it expects and what it needs from the container it is given. |
| [`envelope.schema.json`](envelope.schema.json) | `https://schemas.agentiik.dev/envelope.schema.json` | `{ meta, items }`, the one document that travels along a port. |

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

Five things fail the build:

1. a schema that is not a legal JSON Schema 2020-12 document, that does not carry the
   `$id` it is published under, or that holds a `$ref` leading nowhere;
2. a keyword without a `description` or without `examples`;
3. an example that does not validate against the keyword it illustrates;
4. a fixture that does not behave as `fixtures/index.json` says it does;
5. an em dash, anywhere in any text file.

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
| `secret.provider` | Three providers named in prose, built-in encrypted store, HashiCorp Vault and API environment variables, and exactly one spelling written in a file, `vault`. | A non-empty string. An enum needs three spellings and the documentation gives one, so guessing the other two would put words in a file that has to resolve them. |

### Bounds the documentation implies and does not state

| Where | Reading taken |
| --- | --- |
| `strategy.fan_out`, `batch(n)` | The size starts at one. `batch(n)` is one container per batch of n items, and a batch of zero is a shard that can never be filled. The pattern also refuses the leading-zero spelling `batch(007)`. |
| `resources.cpu`, `resources.memory` | Above zero, in both documents. A CPU allowance of zero is how a container is given no limit at all, and a memory ceiling of zero would stop the container before it started. This matches `pids`, `max_parallel` and `retain.fetches`, each of which the documentation bounds away from zero by what it says the value is for. |
| `include`, `step.needs`, `step.outputs` | At least one entry, and `needs` and `outputs` hold no duplicate. An empty list means exactly what omitting the key means, and a duplicated edge would concatenate one envelope twice. `mcp.tools` is deliberately left unbounded, because the documentation says an empty tool list serves a server with nothing on it and that this differs from declaring no block. |
| `mcpTool.timeout` | Bounded by the 120 second ceiling the documentation states, so `120s`, `2m` and `120000ms` are the longest forms the grammar accepts. The rule sits beside its companion, that an async tool carries no timeout, rather than being left to a validator that would have nothing to read but the literal in the file. |
| `include`, a path with a `ref` | Refused. A path include resolves inside the same commit, so it can never be stale and there is nothing for a ref to pin, which is the reasoning that also refuses a timeout on an async tool. |
| `step`, `workflow` beside the script keywords | Refused. `script` commands run inside `image` and `workflow` is an alternative to `image`, so a sub-workflow call has no container for a script, a shell, a `before_script` or an `after_script` to run in. |

### Named by the documentation, not placed by it

| Name | What is missing | Reading taken |
| --- | --- | --- |
| `grace` | The step keyword table names a grace period on the `timeout` row, between SIGTERM and SIGKILL, and places it in runner policy: no keyword in the file sets it. | No keyword is declared, and none is left to declare. The value belongs to the runner rather than to the workflow. Recorded as a `$comment` on `workflow.$defs/timeout`. |
| A sync webhook response | `response: sync` "returns a named workflow output", and no key names which output. | The enum stays bare. A workflow cannot yet write what the sentence describes, and a companion key would be one this release made up. Recorded as a `$comment` on `webhookTrigger.response`. |
| An exit code in a manifest | The exit code table reserves 121 to 124 for the runner and says a brick exiting with one has failed the contract whatever its manifest says, and no manifest property carries a code. | No definition is published, and no keyword either: a manifest has nothing to say about an exit code. The range is 0 success, 1 to 99 application failure, 100 to 119 transient, 120 invalid input, 121 to 124 reserved for the runner, 125 and above reserved for the runtime; it is kept here rather than as a `$defs` entry nothing refers to, because the language reference is a projection of these documents and would otherwise teach a manifest key that does not exist. |
| A brick's secret name meeting a workflow's | The manifest names what it needs and "the workflow decides which secret of its own namespace answers that name", and no keyword expresses that mapping. | Both names are written on one grammar, so that a manifest cannot require a name no workflow is able to declare. The mount path `/agk/secrets/<name>` is the only link the two documents draw, and they now spell it the same way. |
| `run_id`, in the envelope | A run "carries a ULID", which is twenty-six Crockford base32 characters, while every run identifier the documentation prints is shorter and no two are the same length: twenty in the envelope, fifteen and twelve in the task message. | No length is imposed. A twenty-six character pattern would refuse the documentation's own example. Recorded as a `$comment` on `envelope.meta.run_id`. |

### Shapes the schemas allow that the documentation does not show

| Where | Reading taken |
| --- | --- |
| `on` | Three of the seven kinds of trigger. `manual` is started at the API with its inputs supplied there, `mcp` is declared in the `mcp` block, and `terraform` and `workflow` are the caller's to make, so none of the four is written in this file. The documentation's own `on` block shows exactly these three. Recorded as a `$comment` on the block. |
| Hidden blocks | Accepted at the root of the entry point and under `steps`. The documentation shows them at the root of an included file only, and it defines a hidden block as a name starting with a dot that is never executed, which is true in either place. |
| `steps` | Not required at the root. The documentation lists no required keys beyond what a reader needs to know which document it is holding, and a file declaring inputs and a published surface with its graph in an include is a file this cannot refuse without a rule to refuse it by. |
| `defaults` | Sixteen keys where the documentation's example writes six. A default is defined as what a step inherits where it states nothing of its own, so every step keyword that is a setting rather than graph shape belongs here; `image`, `script`, `needs`, `inputs`, `outputs`, `params`, `if`, `merge`, `strategy`, `extends` and `workflow` say what the step is and what it depends on, and are refused. |
| `brick.runtime.user` | The refusal of root reads the uid half, so `nobody:0` is accepted. The documentation states the rule as a non-root user and justifies it by a process running as uid 0, and says nothing about the group. Recorded as a `$comment` beside the pattern. |
| `envelope.item` | `id`, `data` and `files` are all required. The documentation writes every item with all three and says an item with nothing attached carries an empty list, so absent is never the same as empty here. |

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
