# schemas

The contract every other repository reads: JSON Schema 2020-12 documents for the
workflow file, the brick manifest and the envelope, plus the OpenAPI document of the
API.

Every keyword carries a `description` and `examples`, and the build fails without them,
because the language reference on the site and the `workflow.language` MCP tool are both
generated from here. A language that is documented in three places teaches three
different languages.

This repository is versioned and released on its own, and pinned by every repository
that consumes it: the core, the bricks, the console, the iOS application and the Android
application. A schema change is a release here first.

Nothing is written yet. What the schemas are being written against is the specification
at <https://agentiik.github.io/docs>.

## Licence

Apache-2.0, see [LICENSE](LICENSE). Permissive on purpose: everything here ends up inside
somebody else's brick or client, and copyleft would reach into work that has nothing to
do with the engine. [LICENSING.md](https://github.com/agentiik/.github/blob/main/LICENSING.md) has the reasoning.

## Contributing

[CONTRIBUTING.md](https://github.com/agentiik/.github/blob/main/CONTRIBUTING.md), under the Developer Certificate of Origin 1.1.
