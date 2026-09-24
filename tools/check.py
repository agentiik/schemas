#!/usr/bin/env python3
"""Checks the contract documents of this repository.

Run it with no arguments, from anywhere:

    python tools/check.py

Seven checks run, and all of them run even when an earlier one fails, so one pass
reports everything that is wrong rather than the first thing:

  1. every schema is a legal JSON Schema 2020-12 document, carries the $schema and the
     $id it is published under, and every $ref inside it resolves;
  2. every keyword carries a description and examples;
  3. every example validates against the subschema that carries it;
  4. every fixture behaves as fixtures/index.json says it does, which means every valid
     fixture is accepted and every invalid one is refused by whatever the index says
     refuses it;
  5. no em dash appears in any text file of the repository;
  6. every pattern is one Go, Rust and every other RE2 engine can compile;
  7. a grammar written in more than one document reads the same in each of them.

Check 2 is the one the documentation asks for by name: the language reference on the
site and the workflow.language tool are projections of the description and examples
fields of these schemas, so a keyword without them is a keyword the language reference
cannot teach. It is enforced here rather than left to a reviewer.

Exit status is 0 when everything passes and 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
except ImportError as missing:  # pragma: no cover, this is the first-run message
    sys.exit(
        "%s. Install the pinned dependencies first:\n"
        "    python -m pip install -r requirements.txt" % missing
    )


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"
INDEX = FIXTURES / "index.json"

# Fixture group name, and what the fixtures in that group validate against: a document,
# and a pointer into it where the group pins one message of a family rather than a whole
# document. fixtures/index.json names the same pairs, and check 4 refuses to run if the
# two disagree.
#
# The wire is one document holding many messages because they share a vocabulary, the run
# and task states and the identifiers being the same strings everywhere, and a $ref may
# not leave a document here. A group per message is what lets a fixture still pin one
# message rather than "something the wire allows".
SCHEMAS = {
    "workflow": {"file": "workflow.schema.json"},
    "brick": {"file": "brick.schema.json"},
    "envelope": {"file": "envelope.schema.json"},
    "task-message": {"file": "wire.schema.json", "pointer": "#/$defs/taskMessage"},
    "task-result": {"file": "wire.schema.json", "pointer": "#/$defs/taskResult"},
    "runner-registration": {"file": "wire.schema.json", "pointer": "#/$defs/runnerRegistration"},
    "runner-heartbeat": {"file": "wire.schema.json", "pointer": "#/$defs/runnerHeartbeat"},
    "runner-rotation": {"file": "wire.schema.json", "pointer": "#/$defs/runnerRotation"},
    "grant-redemption": {"file": "wire.schema.json", "pointer": "#/$defs/grantRedemption"},
    "log-shipment": {"file": "wire.schema.json", "pointer": "#/$defs/logShipment"},
    "runner-pool": {"file": "wire.schema.json", "pointer": "#/$defs/runnerPool"},
    "stop": {"file": "wire.schema.json", "pointer": "#/$defs/stop"},
}


def schema_file(name):
    """The document a fixture group validates against."""
    return SCHEMAS[name]["file"]


def schema_pointer(name):
    """The pointer into that document, or None for the document itself."""
    return SCHEMAS[name].get("pointer")

# What the index may say refuses an invalid fixture. See check_fixtures.
REFUSED_BY = ("schema", "validator")

DIALECT = "https://json-schema.org/draft/2020-12/schema"
ID_PREFIX = "https://schemas.agentiik.dev/"

# The author has ruled the em dash out of every description, comment and line of prose
# here. Built from its code point so that this file never carries the character it
# refuses, and so that the check does not report itself.
EM_DASH = chr(0x2014)

# Files the em dash check reads. LICENSE has no suffix and is left alone.
TEXT_SUFFIXES = {".json", ".yaml", ".yml", ".md", ".py"}

# Directories it does not descend into. A virtualenv built inside the repository holds
# thousands of files nobody here wrote, and the house rule is about what this repository
# says, not about what its dependencies say.
SKIP_DIRS = {".git", ".venv", "venv", "env", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache"}


# --------------------------------------------------------------------------------------
# Walking a schema
#
# The 2020-12 applicator keywords, grouped by the shape of their value. Walking through
# exactly these, and never through examples, default, const or enum, is what keeps the
# walk on schemas: an example of the vars block is an object whose keys look like
# properties, and descending into it would invent keywords that nobody wrote.
# --------------------------------------------------------------------------------------

# Keywords whose value maps a name to a subschema.
MAP_OF_SUBSCHEMAS = ("properties", "patternProperties", "$defs", "dependentSchemas")

# Keywords whose value is a single subschema.
ONE_SUBSCHEMA = (
    "items",
    "contains",
    "additionalProperties",
    "propertyNames",
    "not",
    "if",
    "then",
    "else",
    "unevaluatedItems",
    "unevaluatedProperties",
    "contentSchema",
)

# Keywords whose value is a list of subschemas.
LIST_OF_SUBSCHEMAS = ("allOf", "anyOf", "oneOf", "prefixItems")

# Applicators that constrain a value rather than declare one. A properties entry under
# any of these restates a keyword declared elsewhere, so it is not a declaration of its
# own: the mode entry under mcpTool's dependentSchemas is the keyword mode being
# constrained, not a second keyword called mode.
CONSTRAINTS = ("not", "if", "then", "else", "dependentSchemas")


class Subschema:
    """One subschema found inside a document, and what its position says about it."""

    def __init__(self, pointer, schema, name=None, constrained=False):
        self.pointer = pointer  # JSON Pointer from the root of the document
        self.schema = schema
        self.name = name  # the keyword name, when this subschema declares one
        self.constrained = constrained  # reached through not, if, then, else

    @property
    def declares_a_keyword(self):
        return self.name is not None and not self.constrained


def walk(node, pointer="", name=None, constrained=False):
    """Yields every subschema of a document, the root included, in reading order."""
    if not isinstance(node, dict):
        # A subschema may legally be a boolean. It declares nothing and carries no
        # annotation, so there is nothing below it to visit.
        return
    yield Subschema(pointer, node, name, constrained)

    for keyword in MAP_OF_SUBSCHEMAS:
        entries = node.get(keyword)
        if not isinstance(entries, dict):
            continue
        below = constrained or keyword in CONSTRAINTS
        for entry, subschema in entries.items():
            here = "%s/%s/%s" % (pointer, keyword, entry)
            # $defs entries are named, and so are the entries of properties and
            # patternProperties. A name is what makes a subschema a keyword.
            yield from walk(subschema, here, entry, below)

    for keyword in ONE_SUBSCHEMA:
        subschema = node.get(keyword)
        if isinstance(subschema, dict):
            below = constrained or keyword in CONSTRAINTS
            yield from walk(subschema, "%s/%s" % (pointer, keyword), None, below)

    for keyword in LIST_OF_SUBSCHEMAS:
        entries = node.get(keyword)
        if not isinstance(entries, list):
            continue
        for index, subschema in enumerate(entries):
            here = "%s/%s/%d" % (pointer, keyword, index)
            yield from walk(subschema, here, None, constrained)


def resolve_pointer(document, pointer):
    """Follows a JSON Pointer, returning None when it leads nowhere."""
    node = document
    for token in pointer.lstrip("#").split("/"):
        if token == "":
            continue
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and token in node:
            node = node[token]
        elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
            node = node[int(token)]
        else:
            return None
    return node


# --------------------------------------------------------------------------------------
# Reading fixtures
# --------------------------------------------------------------------------------------


class WorkflowLoader(yaml.SafeLoader):
    """YAML as the engine reads it, which is YAML 1.2 rather than YAML 1.1.

    YAML 1.1 resolves on, off, yes and no as booleans. The trigger block of a workflow is
    written `on:`, so under those rules the key of every workflow that declares a trigger
    would arrive as True and be refused by a schema that expects a name. YAML 1.2 keeps
    them as strings, and so does this loader.
    """


WorkflowLoader.yaml_implicit_resolvers = {
    first: [(tag, pattern) for tag, pattern in resolvers if tag.endswith(":bool") is False]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
WorkflowLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def read_fixture(path):
    """Reads one fixture, by the rules of the format its name declares."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    return yaml.load(text, Loader=WorkflowLoader)


def non_string_keys(node, trail=""):
    """Yields the trail of every mapping key that did not arrive as a string.

    A key that is not a string is almost always a quoting accident: YAML reads 0444 as a
    number and 65532:65532 as one too. The schema would refuse the fixture, but for a
    reason that has nothing to do with what the fixture was written to pin, so it is
    worth its own message.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if not isinstance(key, str):
                yield "%s/%r" % (trail, key)
            yield from non_string_keys(value, "%s/%s" % (trail, key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from non_string_keys(value, "%s/%d" % (trail, index))


# --------------------------------------------------------------------------------------
# The checks
# --------------------------------------------------------------------------------------


class Report:
    """Collects failures so that one run says everything that is wrong."""

    def __init__(self, verbose=False):
        self.failures = []
        self.verbose = verbose

    def fail(self, where, message):
        self.failures.append((where, message))

    def note(self, message):
        if self.verbose:
            print("    %s" % message)

    def heading(self, message):
        print("  %s" % message)


def validator_for(document, subschema):
    """Builds a validator for one subschema of a document.

    A subschema lifted out of its document loses the base the $ref pointers inside it
    were written against, so it is handed the document's $defs and validated as a
    document of its own. Nothing here has an $id or a $ref that leaves the file, which is
    what makes that safe.
    """
    if subschema is document:
        return Draft202012Validator(document)
    standalone = dict(subschema)
    if "$defs" in document and "$defs" not in standalone:
        standalone["$defs"] = document["$defs"]
    return Draft202012Validator(standalone)


def check_schemas_are_legal(documents, report):
    """Check 1: the documents are JSON Schema 2020-12, published where they say.

    Returns the documents that came through it. A document the metaschema refuses, or
    one holding a reference that leads nowhere, cannot be used to validate anything, so
    the checks below it are told to leave it alone rather than crash on it.
    """
    sound = {}
    for name, document in documents.items():
        where = name
        usable = True

        if document.get("$schema") != DIALECT:
            report.fail(where, "$schema is not %s" % DIALECT)
        expected_id = ID_PREFIX + name
        if document.get("$id") != expected_id:
            report.fail(where, "$id is %r, expected %r" % (document.get("$id"), expected_id))

        try:
            Draft202012Validator.check_schema(document)
        except SchemaError as error:
            # The full report of a metaschema failure runs to a screen. The message and
            # the place it happened are the two lines a reader needs.
            at = "/".join(str(step) for step in error.absolute_path)
            report.fail(where, "the metaschema refuses it: %s at /%s" % (error.message, at))
            usable = False
        except Exception as error:  # a document too broken to reach the metaschema
            report.fail(where, "not a legal JSON Schema 2020-12 document: %s" % error)
            usable = False

        for found in walk(document):
            reference = found.schema.get("$ref")
            if not isinstance(reference, str):
                continue
            if not reference.startswith("#"):
                report.fail(
                    where,
                    "%s refers to %s, outside this document" % (found.pointer, reference),
                )
                usable = False
            elif resolve_pointer(document, reference) is None:
                report.fail(where, "%s refers to %s, which is not there" % (found.pointer, reference))
                usable = False

        if usable:
            sound[name] = document
            report.heading("%s is a legal JSON Schema 2020-12 document" % where)
        else:
            report.heading("%s is not a usable document, the checks below skip it" % where)
    return sound


def check_every_keyword_is_documented(documents, report):
    """Check 2: the rule the documentation states, enforced by the build.

    A keyword is an entry of properties, of patternProperties or of $defs: a name an
    author writes in their document, or a definition the reference is projected through.
    A branch of a oneOf and the items of an array are shapes rather than keywords, and
    an entry restated under not, if, then, else or dependentSchemas is a constraint on a
    keyword declared elsewhere, so neither is asked for prose of its own.
    """
    for name, document in documents.items():
        where = name
        counted = 0

        # A document that is a family of messages rather than one message has nothing at
        # its root to illustrate: the wire holds the task message, the task result and the
        # rest under $defs, and a reader validates against the member it is holding. Such a
        # root still says what the document is; it is only asked for an example of an
        # instance when it describes one.
        family = not any(key in document for key in ("type", "properties", "items", "enum", "const", "oneOf", "anyOf", "allOf"))

        for found in walk(document):
            if found.pointer != "" and not found.declares_a_keyword:
                continue
            subject = found.name or "the document itself"
            counted += 1

            description = found.schema.get("description")
            if not isinstance(description, str) or not description.strip():
                report.fail(where, "%s (%s) has no description" % (found.pointer or "/", subject))

            if found.pointer == "" and family:
                continue

            examples = found.schema.get("examples")
            if not isinstance(examples, list):
                report.fail(where, "%s (%s) has no examples" % (found.pointer or "/", subject))
            elif not examples:
                report.fail(where, "%s (%s) has an empty examples list" % (found.pointer or "/", subject))

        report.heading("%s: %d keywords, each with a description and examples" % (where, counted))


def check_every_example_validates(documents, report):
    """Check 3: an example that does not validate teaches syntax the engine refuses."""
    for name, document in documents.items():
        where = name
        counted = 0

        for found in walk(document):
            examples = found.schema.get("examples")
            if not isinstance(examples, list):
                continue
            validator = validator_for(document, found.schema)
            for index, example in enumerate(examples):
                counted += 1
                try:
                    errors = sorted(validator.iter_errors(example), key=lambda error: error.json_path)
                except Exception as error:
                    report.fail(where, "%s cannot be validated against: %s" % (found.pointer or "/", error))
                    break
                if errors:
                    report.fail(
                        where,
                        "%s/examples/%d does not validate: %s at %s"
                        % (found.pointer or "", index, errors[0].message, errors[0].json_path),
                    )

        report.heading("%s: %d examples, each valid against the keyword it illustrates" % (where, counted))


def read_index(report):
    """Reads fixtures/index.json, the record of what every fixture pins."""
    if not INDEX.is_file():
        report.fail("fixtures/index.json", "is missing, and it is what says what each fixture pins")
        return None
    try:
        index = json.loads(INDEX.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        report.fail("fixtures/index.json", "is not valid JSON: %s" % error)
        return None

    # The index names the schema each group validates against. It saying one thing while
    # this script does another is the drift both of them exist to prevent.
    listed = index.get("schemas")
    if not isinstance(listed, dict):
        report.fail("fixtures/index.json", "does not say which schema each group validates against")
        return None
    for name, relative in sorted(listed.items()):
        if name not in SCHEMAS:
            report.fail("fixtures/index.json", "names a group, %s, that this check knows nothing about" % name)
        elif (FIXTURES / relative).resolve() != (ROOT / schema_file(name)).resolve():
            report.fail("fixtures/index.json", "points %s at %s, expected %s" % (name, relative, schema_file(name)))
    for name in sorted(set(SCHEMAS) - set(listed)):
        report.fail("fixtures/index.json", "lists no fixtures for %s" % name)
    return index


def check_fixtures(documents, report):
    """Check 4: every fixture behaves as the index says it does.

    A fixture under valid/ has to be accepted. A fixture under invalid/ has to be refused
    when the index says the schema refuses it, and accepted when the index says the
    workflow validator does: those pin a rule the documentation states and JSON Schema
    cannot express, because it needs the graph, a brick manifest, an included file or the
    expression language. Asserting that they are schema valid is what keeps that claim
    honest, and what catches a schema that starts refusing them for some other reason.

    An invalid fixture quietly accepted is the failure this check exists for: the schema
    stopped refusing something it was written to refuse.
    """
    index = read_index(report)
    if index is None:
        return

    groups = index.get("fixtures")
    if not isinstance(groups, dict):
        report.fail("fixtures/index.json", "carries no fixtures")
        return

    # Everything the index lists, gathered before any of it is validated. A group whose
    # schema did not survive check 1 is not validated here, but its files are still
    # listed, so the sweep at the end does not report every one of them as unindexed on
    # top of the failure that is already being reported.
    listed_paths = set()
    for group in groups.values():
        if not isinstance(group, dict):
            continue
        for entries in group.values():
            for entry in entries if isinstance(entries, list) else []:
                if isinstance(entry, dict) and isinstance(entry.get("file"), str):
                    listed_paths.add((FIXTURES / entry["file"]).resolve())

    # The groups that were validated, so that one skipped in silence is caught below.
    checked = set()

    for name in sorted(groups):
        if name not in SCHEMAS or schema_file(name) not in documents:
            # Either the index names a group this check does not know, which read_index
            # has already reported, or the schema behind it did not survive check 1.
            continue
        checked.add(name)
        document = documents[schema_file(name)]
        pointer = schema_pointer(name)
        subschema = document if pointer is None else resolve_pointer(document, pointer)
        if subschema is None:
            report.fail(schema_file(name), "%s points at %s, which is not there" % (name, pointer))
            continue
        validator = validator_for(document, subschema)
        group = groups[name] if isinstance(groups[name], dict) else {}
        accepted = refused = deferred = aside = 0

        for verdict in ("valid", "invalid"):
            entries = group.get(verdict)
            if not isinstance(entries, list) or not entries:
                report.fail("fixtures/index.json", "lists no %s fixtures for %s" % (verdict, name))
                continue

            for entry in entries:
                relative = entry.get("file") if isinstance(entry, dict) else None
                if not isinstance(relative, str):
                    report.fail("fixtures/index.json", "a %s entry under %s names no file" % (verdict, name))
                    continue
                path = FIXTURES / relative
                where = "fixtures/%s" % relative

                if not path.is_file():
                    report.fail(where, "is listed in the index and is not there")
                    continue

                # The index is the documentation of the fixture set, so an entry that
                # says nothing is as much a failure as a fixture that misbehaves.
                if verdict == "valid" and not str(entry.get("covers", "")).strip():
                    report.fail(where, "is listed without saying what it covers")
                if verdict == "invalid" and not str(entry.get("rule", "")).strip():
                    report.fail(where, "is listed without the rule it breaks")

                refused_by = entry.get("refused_by") if verdict == "invalid" else None
                if verdict == "invalid" and refused_by not in REFUSED_BY:
                    report.fail(where, "says it is refused by %r, expected one of %s" % (refused_by, " or ".join(REFUSED_BY)))
                    continue

                try:
                    fixture = read_fixture(path)
                except Exception as error:
                    report.fail(where, "cannot be read: %s" % error)
                    continue

                misread = list(non_string_keys(fixture))
                if misread:
                    report.fail(where, "these keys did not arrive as strings, quote them: %s" % ", ".join(misread))
                    continue

                # An entry carrying a role says the file is a document of another kind:
                # an included file is a fragment merged into an entry point and has no
                # apiVersion of its own, so validating it against the entry point schema
                # would refuse it for a reason that has nothing to do with what it pins.
                # The build asserts it is there and reads, and leaves the rest alone.
                role = str(entry.get("role", "")).strip()
                if role:
                    aside += 1
                    report.note("%s: %s, read but not validated" % (relative, role))
                    continue

                errors = sorted(validator.iter_errors(fixture), key=lambda error: error.json_path)
                first = "%s at %s" % (errors[0].message, errors[0].json_path) if errors else ""

                if verdict == "valid":
                    if errors:
                        report.fail(where, "should be accepted, refused: %s" % first)
                    else:
                        accepted += 1
                        report.note("accepted %s" % relative)
                elif refused_by == "schema":
                    if errors:
                        refused += 1
                        report.note("refused %s: %s" % (relative, first))
                    else:
                        report.fail(where, "should be refused by the schema, was accepted")
                else:  # refused_by == "validator"
                    if errors:
                        report.fail(
                            where,
                            "is left to the validator, so the schema should accept it, refused: %s" % first,
                        )
                    else:
                        deferred += 1
                        report.note("schema valid on purpose, left to the validator: %s" % relative)

        summary = "%s: %d fixtures accepted, %d refused, %d left to the validator" % (
            name if schema_pointer(name) else schema_file(name),
            accepted,
            refused,
            deferred,
        )
        if aside:
            summary += ", %d read as documents of another kind" % aside
        report.heading(summary)

    # A group whose schema came through check 1 and whose fixtures were never validated is
    # the failure this check can least afford, because it looks like success: the build
    # printed that everything checks out while looking at no fixture at all, from the day
    # the documents came to be keyed by file and the groups stayed keyed by message.
    for name in sorted(set(SCHEMAS) - checked):
        if schema_file(name) in documents:
            report.fail("fixtures/index.json", "the %s fixtures were not validated, and a group skipped in silence proves nothing" % name)

    # A fixture nobody indexed is a fixture nobody documented, and the build has no way
    # to know what it was supposed to prove.
    for path in sorted(FIXTURES.rglob("*")):
        if not path.is_file() or path == INDEX:
            continue
        if path.resolve() not in listed_paths:
            report.fail(str(path.relative_to(ROOT)), "is not listed in fixtures/index.json")


def check_no_em_dash(report):
    """Check 5: the house rule, which a description written elsewhere tends to carry in."""
    counted = 0
    for path in sorted(ROOT.rglob("*")):
        if SKIP_DIRS.intersection(path.parts) or not path.is_file():
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        counted += 1
        where = str(path.relative_to(ROOT))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if EM_DASH in line:
                report.fail(where, "line %d holds an em dash, use a comma, a colon, a semicolon or a new sentence" % number)
    report.heading("%d text files, none holding an em dash" % counted)


RE2_CANNOT = (
    ("(?=", "a lookahead"),
    ("(?!", "a negative lookahead"),
    ("(?<=", "a lookbehind"),
    ("(?<!", "a negative lookbehind"),
    ("\\u", "a \\u escape, which is \\x in every engine that is not ECMA-262"),
    ("\\1", "a backreference"),
    ("(?P<", "a named group of the Python spelling"),
)


def patterns_in(node, pointer=""):
    """Yields every pattern in a document, with the pointer that names it."""
    if isinstance(node, dict):
        if isinstance(node.get("pattern"), str):
            yield pointer + "/pattern", node["pattern"]
        for key, value in node.items():
            yield from patterns_in(value, pointer + "/" + str(key).replace("~", "~0").replace("/", "~1"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from patterns_in(value, pointer + "/%d" % index)


def check_every_pattern_is_portable(documents, report):
    """Check 6: a pattern every consumer can compile, not only the ones with a backtracking engine.

    JSON Schema says pattern is ECMA-262, and a lookahead is legal there. It is also
    unreadable to Go, to Rust and to everything else built on RE2, which refuse the
    whole document rather than the one keyword. A schema exists so that a consumer can
    hold a message to it, and a schema only some consumers can read is half a schema.

    What a lookahead expressed, a `not` beside the pattern expresses too, and every
    engine reads that.
    """
    counted = 0
    for filename, document in sorted(documents.items()):
        for pointer, pattern in patterns_in(document):
            counted += 1
            for fragment, what in RE2_CANNOT:
                if fragment in pattern:
                    report.fail(
                        filename,
                        "%s holds %s, which Go, Rust and every other RE2 engine refuse: %s"
                        % (pointer, what, pattern),
                    )
                    break
    report.heading("%d patterns, each one every engine can compile" % counted)


# Grammars written in more than one document. A $ref may not leave a document here, so a
# grammar two documents share is two copies of it, and the copies drifting apart is the
# very fault the sharing exists to prevent: a secret mount the manifest accepted and the
# grant redemption refused was a secret the engine dispatched and a strict runner could
# not write. Each entry names what the grammar is for and every place it is written.
ONE_GRAMMAR = (
    (
        "a secret mount",
        (
            ("wire.schema.json", "#/$defs/secretMount/pattern"),
            ("brick.schema.json", "#/$defs/secret/properties/mount/pattern"),
        ),
    ),
    (
        "a name the workflow file writes",
        (
            ("workflow.schema.json", "#/$defs/identifier/pattern"),
            ("brick.schema.json", "#/$defs/portName/pattern"),
            ("brick.schema.json", "#/$defs/secret/properties/name/pattern"),
            ("wire.schema.json", "#/$defs/identifier/pattern"),
            ("envelope.schema.json", "#/$defs/identifier/pattern"),
        ),
    ),
    (
        "a parameter name",
        (
            ("workflow.schema.json", "#/$defs/paramName/pattern"),
            ("brick.schema.json", "#/$defs/paramName/pattern"),
            ("wire.schema.json", "#/$defs/taskMessage/properties/params/propertyNames/pattern"),
        ),
    ),
    (
        "the words a namespace may not be",
        (
            ("wire.schema.json", "#/$defs/namespace/not/pattern"),
            ("workflow.schema.json", "#/$defs/namespace/not/pattern"),
        ),
    ),
    (
        "the words a workflow path may not start with",
        (
            ("workflow.schema.json", "#/$defs/workflowPath/not/pattern"),
            ("workflow.schema.json", "#/$defs/step/properties/workflow/oneOf/0/not/pattern"),
        ),
    ),
)


def check_every_copy_agrees(documents, report):
    """Check 7: a grammar written in several documents reads the same in each of them.

    The first place an entry of ONE_GRAMMAR names is the one the others are held to, so
    a failure names both pointers and both patterns, and a reader can see which copy moved
    without opening either document.
    """
    for what, copies in ONE_GRAMMAR:
        written = []
        for filename, pointer in copies:
            if filename not in documents:
                # A document that did not load has been reported already.
                continue
            pattern = resolve_pointer(documents[filename], pointer)
            if not isinstance(pattern, str):
                report.fail(filename, "%s is where the grammar of %s is written, and holds no pattern" % (pointer, what))
                continue
            written.append((filename, pointer, pattern))

        for filename, pointer, pattern in written[1:]:
            first_file, first_pointer, first = written[0]
            if pattern != first:
                report.fail(
                    filename,
                    "%s reads %s and %s%s reads %s, and both are the grammar of %s"
                    % (pointer, pattern, first_file, first_pointer, first, what),
                )
    report.heading("%d grammars, each written the same wherever it is copied" % len(ONE_GRAMMAR))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="name every fixture, and say why each refused one was refused",
    )
    arguments = parser.parse_args()
    report = Report(verbose=arguments.verbose)

    # Keyed by file rather than by group, because the wire is one document holding
    # several groups and reporting it three times over would be three copies of one fault.
    documents = {}
    for filename in sorted({entry["file"] for entry in SCHEMAS.values()}):
        path = ROOT / filename
        try:
            documents[filename] = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            report.fail(filename, "is missing")
        except json.JSONDecodeError as error:
            report.fail(filename, "is not valid JSON: %s" % error)

    if documents:
        print("Schemas")
        # Checks 3 and 4 validate through the documents, so they only see the ones that
        # can be validated through. Check 2 only reads, and reads them all.
        sound = check_schemas_are_legal(documents, report)
        print("Keywords")
        check_every_keyword_is_documented(documents, report)
        print("Examples")
        check_every_example_validates(sound, report)
        print("Fixtures")
        check_fixtures(sound, report)
        print("Patterns")
        check_every_pattern_is_portable(documents, report)
        print("Grammars")
        check_every_copy_agrees(documents, report)
    print("Prose")
    check_no_em_dash(report)

    if report.failures:
        print("\n%d %s:" % (len(report.failures), "failure" if len(report.failures) == 1 else "failures"))
        for where, message in report.failures:
            print("  %s: %s" % (where, message))
        return 1
    print("\nEverything the build checks, checks out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
