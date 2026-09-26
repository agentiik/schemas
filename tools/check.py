#!/usr/bin/env python3
"""Checks the contract documents of this repository.

Run it with no arguments, from anywhere:

    python tools/check.py

Ten checks run, and all of them run even when an earlier one fails, so one pass
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
  7. a grammar written in more than one document reads the same in each of them, and a
     grammar written inside a longer pattern reads the same as where it is defined;
  8. openapi.json is an OpenAPI 3.1 document whose schemas are JSON Schema 2020-12: it
     carries the fields a reader needs, every path parameter is declared and every declared
     one is in its path, every operationId is unique, and every $ref resolves, inside it or
     in a schema of this repository;
  9. every operation, parameter, request body, response, header and schema in it carries a
     description and examples, and every example validates against what it illustrates;
 10. the routes it describes and the route table of the documentation agree: a route in one
     and not in the other fails, unless NOT_DESCRIBED_YET names it and says why.

Check 2 is the one the documentation asks for by name: the language reference on the
site and the workflow.language tool are projections of the description and examples
fields of these schemas, so a keyword without them is a keyword the language reference
cannot teach. It is enforced here rather than left to a reviewer. Check 9 is the same rule
for the API, whose reference and clients are generated from openapi.json.

Check 10 reads the documentation, from the site by default and from a checkout with
--docs, because the documentation decides which routes exist and this document follows it.

Exit status is 0 when everything passes and 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

try:
    import yaml
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
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
    "task-progress": {"file": "wire.schema.json", "pointer": "#/$defs/taskProgress"},
    "runner-registration": {"file": "wire.schema.json", "pointer": "#/$defs/runnerRegistration"},
    "runner-heartbeat": {"file": "wire.schema.json", "pointer": "#/$defs/runnerHeartbeat"},
    "runner-rotation": {"file": "wire.schema.json", "pointer": "#/$defs/runnerRotation"},
    "grant-redemption": {"file": "wire.schema.json", "pointer": "#/$defs/grantRedemption"},
    "log-shipment": {"file": "wire.schema.json", "pointer": "#/$defs/logShipment"},
    "runner-pool": {"file": "wire.schema.json", "pointer": "#/$defs/runnerPool"},
    "stop": {"file": "wire.schema.json", "pointer": "#/$defs/stop"},
    "principal": {"file": "wire.schema.json", "pointer": "#/$defs/principal"},
    "principal-ref": {"file": "wire.schema.json", "pointer": "#/$defs/principalRef"},
    "credential": {"file": "wire.schema.json", "pointer": "#/$defs/credential"},
    "api-token": {"file": "wire.schema.json", "pointer": "#/$defs/apiToken"},
    "access-grant": {"file": "wire.schema.json", "pointer": "#/$defs/accessGrant"},
    "role": {"file": "wire.schema.json", "pointer": "#/$defs/role"},
    "permission": {"file": "wire.schema.json", "pointer": "#/$defs/permission"},
    "namespace-record": {"file": "wire.schema.json", "pointer": "#/$defs/namespaceRecord"},
    "auth-policy": {"file": "wire.schema.json", "pointer": "#/$defs/authPolicy"},
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


# Grammars written inside a longer pattern. A principal reference is one string holding a
# name, group:team-finance or finance/agentiik, and JSON Schema has no way to build a
# pattern out of another one, so the name grammar is written again inside it. Each entry
# names what the pattern is, where it is written, how it is composed, and the patterns it
# is composed of: {0} stands for the first of them without its anchors, {1} for the
# second. The composed pattern has to be exactly the template filled in, so a name
# grammar that moves takes every reference written on it along, or the build fails.
COMPOSED_GRAMMAR = (
    (
        "a group reference",
        ("wire.schema.json", "#/$defs/groupRef/pattern"),
        "^group:{0}$",
        (("wire.schema.json", "#/$defs/namespace/pattern"),),
    ),
    (
        "a service account reference",
        ("wire.schema.json", "#/$defs/serviceAccountRef/pattern"),
        "^{0}/{0}$",
        (("wire.schema.json", "#/$defs/namespace/pattern"),),
    ),
    (
        "a workflow a grant is scoped to",
        ("wire.schema.json", "#/$defs/grantScope/oneOf/1/pattern"),
        "^{0}/{1}$",
        (
            ("wire.schema.json", "#/$defs/namespace/pattern"),
            ("wire.schema.json", "#/$defs/identifier/pattern"),
        ),
    ),
)


def unanchored(pattern):
    """A pattern without the ^ and $ that anchor it, ready to be written inside another."""
    if pattern.startswith("^"):
        pattern = pattern[1:]
    if pattern.endswith("$"):
        pattern = pattern[:-1]
    return pattern


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

    for what, (filename, pointer), template, parts in COMPOSED_GRAMMAR:
        if filename not in documents or any(part_file not in documents for part_file, _ in parts):
            continue
        composed = resolve_pointer(documents[filename], pointer)
        if not isinstance(composed, str):
            report.fail(filename, "%s is where the grammar of %s is written, and holds no pattern" % (pointer, what))
            continue
        pieces = []
        for part_file, part_pointer in parts:
            piece = resolve_pointer(documents[part_file], part_pointer)
            if not isinstance(piece, str):
                report.fail(part_file, "%s is what %s is composed of, and holds no pattern" % (part_pointer, what))
                break
            pieces.append(unanchored(piece))
        else:
            expected = template.format(*pieces)
            if composed != expected:
                report.fail(
                    filename,
                    "%s reads %s, and the grammar of %s composed from %s reads %s"
                    % (pointer, composed, what, ", ".join(p for _, p in parts), expected),
                )
    report.heading("%d composed grammars, each written as the grammars it is made of" % len(COMPOSED_GRAMMAR))


# --------------------------------------------------------------------------------------
# The OpenAPI document
#
# openapi.json describes the routes of /api/v1 for the three clients that speak them. It is
# checked here with the standard library and the jsonschema this file already uses, rather
# than with a validator package: what matters is small enough to say in a page, the shapes
# the clients generate from and the rule every schema here follows, and a dependency that
# brings its own opinions of OpenAPI would be one more thing to pin and to disagree with.
# --------------------------------------------------------------------------------------

OPENAPI = "openapi.json"
OPENAPI_URI = ID_PREFIX + OPENAPI

# 3.1 because it is the version whose schemas are JSON Schema 2020-12, the dialect every
# document of this repository is written in, so that a record the wire defines can be
# referred to rather than copied into a dialect of its own.
OPENAPI_VERSION = re.compile(r"^3\.1\.[0-9]+$")

HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
PATH_ITEM_KEYS = {"summary", "description", "servers", "parameters", "$ref"} | set(HTTP_METHODS)
PARAMETER_LOCATIONS = ("path", "query", "header", "cookie")
STATUS_CODE = re.compile(r"^(?:[1-5][0-9]{2}|[1-5]XX|default)$")
COMPONENT_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
PATH_TEMPLATE = re.compile(r"\{([^}]+)\}")

# OpenAPI 3.0 spellings that 2020-12 reads as unknown keywords and silently ignores: a
# nullable that allows nothing and an example nobody validates are both worse than an
# error. Media types, parameters and headers carry examples, the map, and nothing else, so
# that there is one way to write an example and every one of them is checked.
IGNORED_IN_2020_12 = ("nullable", "example")

# Where each operation's externalDocs points: the section of the documentation that
# specifies it. Check 10 holds the anchor to one the page carries.
DOCS_ANCHOR_PREFIX = "https://agentiik.github.io/docs#"


def pointer_of(tokens):
    """A JSON Pointer written as a URI fragment, each token escaped then percent-encoded."""
    return "".join("/" + quote(str(t).replace("~", "~0").replace("/", "~1"), safe="") for t in tokens)


def readable(tokens):
    """A JSON Pointer for a person: escaped, not percent-encoded."""
    return "".join("/" + str(t).replace("~", "~0").replace("/", "~1") for t in tokens) or "/"


def refs_in(node, tokens=()):
    """Yields every $ref of a document with the tokens of the object holding it."""
    if isinstance(node, dict):
        if isinstance(node.get("$ref"), str):
            yield tokens, node["$ref"]
        for key, value in node.items():
            yield from refs_in(value, tokens + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from refs_in(value, tokens + (index,))


def resolve_ref(reference, openapi, documents):
    """Follows a $ref of openapi.json, returning the target or None.

    A reference either stays in the document or leads to one of the schemas beside it, by
    the file name that is its $id relative to this document's: that is what lets a user or
    a grant be the wire's record rather than a copy of it, and what a consumer resolves
    against the two files sitting side by side.
    """
    target, _, fragment = reference.partition("#")
    if target == "":
        document = openapi
    elif target in documents:
        document = documents[target]
    else:
        return None
    return resolve_pointer(document, fragment)


def followed(node, openapi):
    """A Reference Object of the document replaced by its target, its description kept."""
    if isinstance(node, dict) and isinstance(node.get("$ref"), str) and node["$ref"].startswith("#"):
        target = resolve_pointer(openapi, node["$ref"].partition("#")[2])
        if isinstance(target, dict):
            merged = dict(target)
            for key in ("summary", "description"):
                if key in node:
                    merged[key] = node[key]
            return merged
        return None
    return node


def operations_of(openapi):
    """Yields (path, method, path item, operation) for every operation, in reading order."""
    paths = openapi.get("paths")
    if not isinstance(paths, dict):
        return
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        for method in HTTP_METHODS:
            if isinstance(item.get(method), dict):
                yield path, method, item, item[method]


class Declared:
    """One object the document declares in place: what it is, where, and the object."""

    def __init__(self, kind, tokens, node, name=None):
        self.kind = kind  # parameter, requestBody, response, header, mediaType, schema
        self.tokens = tokens
        self.node = node
        self.name = name  # a component's name, for a schema that is one

    @property
    def where(self):
        return readable(self.tokens)


def declared_in(openapi):
    """Yields every parameter, request body, response, header, media type and schema.

    A Reference Object is not yielded where it is written: its target is, where that is
    declared, so each object is checked once whatever refers to it.
    """

    def is_ref(node):
        return isinstance(node, dict) and "$ref" in node

    def media_types(content, tokens):
        for media, entry in (content or {}).items():
            if not isinstance(entry, dict):
                continue
            here = tokens + ("content", media)
            yield Declared("mediaType", here, entry)
            if isinstance(entry.get("schema"), (dict, bool)):
                yield Declared("schema", here + ("schema",), entry["schema"])

    def header(node, tokens):
        yield Declared("header", tokens, node)
        if isinstance(node.get("schema"), (dict, bool)):
            yield Declared("schema", tokens + ("schema",), node["schema"])

    def parameter(node, tokens):
        yield Declared("parameter", tokens, node)
        if isinstance(node.get("schema"), (dict, bool)):
            yield Declared("schema", tokens + ("schema",), node["schema"])

    def request_body(node, tokens):
        yield Declared("requestBody", tokens, node)
        yield from media_types(node.get("content"), tokens)

    def response(node, tokens):
        yield Declared("response", tokens, node)
        for name, entry in (node.get("headers") or {}).items():
            if isinstance(entry, dict) and not is_ref(entry):
                yield from header(entry, tokens + ("headers", name))
        yield from media_types(node.get("content"), tokens)

    components = openapi.get("components") if isinstance(openapi.get("components"), dict) else {}
    for name, node in (components.get("schemas") or {}).items():
        yield Declared("schema", ("components", "schemas", name), node, name)
    for name, node in (components.get("parameters") or {}).items():
        if isinstance(node, dict) and not is_ref(node):
            yield from parameter(node, ("components", "parameters", name))
    for name, node in (components.get("headers") or {}).items():
        if isinstance(node, dict) and not is_ref(node):
            yield from header(node, ("components", "headers", name))
    for name, node in (components.get("requestBodies") or {}).items():
        if isinstance(node, dict) and not is_ref(node):
            yield from request_body(node, ("components", "requestBodies", name))
    for name, node in (components.get("responses") or {}).items():
        if isinstance(node, dict) and not is_ref(node):
            yield from response(node, ("components", "responses", name))

    for path, item in (openapi.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for index, node in enumerate(item.get("parameters") or []):
            if isinstance(node, dict) and not is_ref(node):
                yield from parameter(node, ("paths", path, "parameters", index))
        for method in HTTP_METHODS:
            operation = item.get(method)
            if not isinstance(operation, dict):
                continue
            here = ("paths", path, method)
            for index, node in enumerate(operation.get("parameters") or []):
                if isinstance(node, dict) and not is_ref(node):
                    yield from parameter(node, here + ("parameters", index))
            body = operation.get("requestBody")
            if isinstance(body, dict) and not is_ref(body):
                yield from request_body(body, here + ("requestBody",))
            for status, node in (operation.get("responses") or {}).items():
                if isinstance(node, dict) and not is_ref(node):
                    yield from response(node, here + ("responses", status))


def check_openapi_is_sound(openapi, documents, report):
    """Check 8: an OpenAPI 3.1 document a generator can read, with nothing leading nowhere.

    Returns whether the checks below it can use the document. One whose references lead
    nowhere cannot have its examples validated, so they are told to leave it alone rather
    than crash on it.
    """
    where = OPENAPI
    usable = True

    if not OPENAPI_VERSION.match(str(openapi.get("openapi", ""))):
        report.fail(where, "openapi is %r, expected 3.1.x" % openapi.get("openapi"))
    # Said outright rather than left to the default, which is OpenAPI's own dialect: the
    # schemas here are read as every other document of this repository is.
    if openapi.get("jsonSchemaDialect") != DIALECT:
        report.fail(where, "jsonSchemaDialect is not %s" % DIALECT)

    info = openapi.get("info") if isinstance(openapi.get("info"), dict) else {}
    for key in ("title", "version", "description"):
        if not str(info.get(key, "")).strip():
            report.fail(where, "info has no %s" % key)

    for index, server in enumerate(openapi.get("servers") or []):
        if not isinstance(server, dict) or not str(server.get("url", "")).strip() or not str(server.get("description", "")).strip():
            report.fail(where, "/servers/%d needs a url and a description" % index)
            continue
        for name, variable in (server.get("variables") or {}).items():
            if "default" not in variable or not str(variable.get("description", "")).strip():
                report.fail(where, "/servers/%d/variables/%s needs a default and a description" % (index, name))

    components = openapi.get("components") if isinstance(openapi.get("components"), dict) else {}
    for section, entries in components.items():
        for name in entries if isinstance(entries, dict) else ():
            if not COMPONENT_NAME.match(name):
                report.fail(where, "/components/%s/%s is not a name OpenAPI allows a component" % (section, name))

    schemes = components.get("securitySchemes") if isinstance(components.get("securitySchemes"), dict) else {}
    for name, scheme in schemes.items():
        if not isinstance(scheme, dict) or not scheme.get("type") or not str(scheme.get("description", "")).strip():
            report.fail(where, "/components/securitySchemes/%s needs a type and a description" % name)

    def check_security(requirements, at):
        if not isinstance(requirements, list):
            report.fail(where, "%s/security is not a list of requirements" % at)
            return
        for requirement in requirements:
            for name in requirement if isinstance(requirement, dict) else ():
                if name not in schemes:
                    report.fail(where, "%s/security names %s, which no securityScheme declares" % (at, name))

    if "security" in openapi:
        check_security(openapi["security"], "")

    declared_tags = {}
    for tag in openapi.get("tags") or []:
        if isinstance(tag, dict) and tag.get("name"):
            declared_tags[tag["name"]] = tag
            if not str(tag.get("description", "")).strip():
                report.fail(where, "the tag %s has no description" % tag["name"])
    used_tags = set()

    paths = openapi.get("paths")
    if not isinstance(paths, dict) or not paths:
        report.fail(where, "describes no path")
        paths = {}

    def parameters_of(node, at):
        """The (name, in) pairs a parameters list declares, references followed."""
        found = {}
        for index, entry in enumerate(node.get("parameters") or []):
            target = followed(entry, openapi)
            if not isinstance(target, dict):
                report.fail(where, "%s/parameters/%d leads nowhere" % (at, index))
                continue
            key = (target.get("name"), target.get("in"))
            if target.get("in") not in PARAMETER_LOCATIONS:
                report.fail(where, "%s/parameters/%d is in %r, expected one of %s" % (at, index, target.get("in"), ", ".join(PARAMETER_LOCATIONS)))
            if key in found:
                report.fail(where, "%s declares the %s parameter %s twice" % (at, key[1], key[0]))
            found[key] = target
        return found

    operation_ids = {}
    counted = 0
    for path, item in paths.items():
        at = readable(("paths", path))
        if not path.startswith("/"):
            report.fail(where, "%s does not start with /" % at)
        if not isinstance(item, dict):
            report.fail(where, "%s is not a path item" % at)
            continue
        for key in item:
            if key not in PATH_ITEM_KEYS and not key.startswith("x-"):
                report.fail(where, "%s holds %s, which a path item does not" % (at, key))

        inherited = parameters_of(item, at)
        templated = set(PATH_TEMPLATE.findall(path))

        for method in HTTP_METHODS:
            operation = item.get(method)
            if not isinstance(operation, dict):
                continue
            counted += 1
            here = readable(("paths", path, method))

            operation_id = operation.get("operationId")
            if not str(operation_id or "").strip():
                report.fail(where, "%s has no operationId" % here)
            elif operation_id in operation_ids:
                report.fail(where, "%s repeats the operationId %s of %s" % (here, operation_id, operation_ids[operation_id]))
            else:
                operation_ids[operation_id] = here

            tags = operation.get("tags")
            if not isinstance(tags, list) or not tags:
                report.fail(where, "%s carries no tag, and a generated client groups by tag" % here)
            for tag in tags or []:
                used_tags.add(tag)
                if tag not in declared_tags:
                    report.fail(where, "%s is tagged %s, which the document does not declare" % (here, tag))

            docs = operation.get("externalDocs")
            if not isinstance(docs, dict) or not str(docs.get("url", "")).startswith(DOCS_ANCHOR_PREFIX):
                report.fail(where, "%s has no externalDocs pointing at the section of %s that specifies it" % (here, DOCS_ANCHOR_PREFIX))

            if "security" in operation:
                check_security(operation["security"], here)

            parameters = dict(inherited)
            parameters.update(parameters_of(operation, here))
            in_path = {name for (name, location) in parameters if location == "path"}
            for name in sorted(templated - in_path):
                report.fail(where, "%s leaves the path parameter {%s} undeclared" % (here, name))
            for name in sorted(in_path - templated):
                report.fail(where, "%s declares a path parameter %s that %s does not hold" % (here, name, path))
            for (name, location), target in parameters.items():
                if location == "path" and target.get("required") is not True:
                    report.fail(where, "%s: the path parameter %s is not required: true, which OpenAPI requires" % (here, name))

            responses = operation.get("responses")
            if not isinstance(responses, dict) or not responses:
                report.fail(where, "%s answers nothing" % here)
                continue
            for status, answer in responses.items():
                if not STATUS_CODE.match(str(status)):
                    report.fail(where, "%s/responses/%s is not a status code" % (here, status))
                target = followed(answer, openapi)
                if not isinstance(target, dict):
                    report.fail(where, "%s/responses/%s leads nowhere" % (here, status))
                elif not str(target.get("description", "")).strip():
                    report.fail(where, "%s/responses/%s has no description, which OpenAPI requires" % (here, status))

    for name in sorted(set(declared_tags) - used_tags):
        report.fail(where, "declares the tag %s and no operation carries it" % name)

    # Every reference, schema or not, leads somewhere: inside the document, or into one of
    # the schemas beside it. A reference anywhere else is one a consumer cannot follow.
    for tokens, reference in refs_in(openapi):
        target = resolve_ref(reference, openapi, documents)
        if target is None:
            usable = False
            report.fail(where, "%s refers to %s, which is not there" % (readable(tokens), reference))

    # Every schema is a legal 2020-12 document, and none uses a keyword 2020-12 ignores.
    for found in declared_in(openapi):
        if found.kind != "schema" or not isinstance(found.node, dict):
            continue
        try:
            Draft202012Validator.check_schema(found.node)
        except SchemaError as error:
            at = "/".join(str(step) for step in error.absolute_path)
            report.fail(where, "%s: the metaschema refuses it: %s at /%s" % (found.where, error.message, at))
            usable = False
        for inner in walk(found.node):
            for keyword in IGNORED_IN_2020_12:
                if keyword in inner.schema:
                    report.fail(where, "%s%s writes %s, which JSON Schema 2020-12 ignores" % (found.where, inner.pointer, keyword))

    report.heading(
        "%s is an OpenAPI 3.1 document: %d operations on %d paths, every reference resolving"
        % (where, counted, len(paths))
    )
    return usable


def check_openapi_is_documented(openapi, report):
    """Check 9, first half: the rule of check 2, for the API.

    The API reference and the clients are generated from this document, so an operation, a
    parameter or a field without a description is one the reference cannot explain, and one
    without an example is one nobody has shown working. A media type, a parameter or a
    header carries its examples as OpenAPI's map; a schema carries them as JSON Schema's
    list, which check 9's second half validates the same way.
    """
    where = OPENAPI
    counts = {"operation": 0, "parameter": 0, "response": 0, "schema": 0}

    for path, method, item, operation in operations_of(openapi):
        counts["operation"] += 1
        here = readable(("paths", path, method))
        for key in ("summary", "description"):
            if not str(operation.get(key, "")).strip():
                report.fail(where, "%s has no %s" % (here, key))

    for found in declared_in(openapi):
        node = found.node
        if found.kind in ("parameter", "header", "requestBody", "response"):
            if not str(node.get("description", "")).strip():
                report.fail(where, "%s (a %s) has no description" % (found.where, found.kind))
        if found.kind in ("parameter", "header", "mediaType"):
            if "example" in node:
                report.fail(where, "%s writes example; write examples, the map, so every one is checked" % found.where)
            if "schema" not in node:
                report.fail(where, "%s (a %s) has no schema" % (found.where, found.kind))
            examples = node.get("examples")
            if not isinstance(examples, dict) or not examples:
                report.fail(where, "%s (a %s) has no examples" % (found.where, found.kind))
            else:
                for name, example in examples.items():
                    example = followed(example, openapi)
                    if not isinstance(example, dict) or "value" not in example:
                        report.fail(where, "%s/examples/%s has no value" % (found.where, name))
        if found.kind == "parameter":
            counts["parameter"] += 1
        if found.kind == "requestBody" and not node.get("content"):
            report.fail(where, "%s is a request body with no content" % found.where)
        if found.kind == "response":
            counts["response"] += 1

        if found.kind == "schema" and isinstance(node, dict):
            # A component is a keyword of the API's language, named and projected into the
            # reference, so it is held to what a $defs entry is held to. A schema written
            # in place is described by the parameter, header or media type holding it, and
            # only the keywords it declares inside are asked for their own.
            for inner in walk(node, "", found.name):
                if inner.pointer == "" and found.name is None:
                    continue
                if inner.pointer != "" and not inner.declares_a_keyword:
                    continue
                counts["schema"] += 1
                subject = inner.name or found.name
                at = found.where + inner.pointer
                if not str(inner.schema.get("description", "")).strip():
                    report.fail(where, "%s (%s) has no description" % (at, subject))
                examples = inner.schema.get("examples")
                if not isinstance(examples, list) or not examples:
                    report.fail(where, "%s (%s) has no examples" % (at, subject))

    report.heading(
        "%s: %d operations, %d parameters, %d responses and %d schema keywords, each with a description and examples"
        % (where, counts["operation"], counts["parameter"], counts["response"], counts["schema"])
    )


def check_openapi_examples_validate(openapi, documents, report):
    """Check 9, second half: every example of the document validates against what it shows.

    The validator resolves a reference into the wire as a consumer does, relative to this
    document, through a registry holding every schema of the repository under its $id and
    this document under the $id it would have. Each example is validated against its schema
    where it stands, by pointer, so that a reference inside it to another component resolves
    against this document and not against the schema lifted out of it.
    """
    where = OPENAPI
    registry = Registry().with_resources(
        [(document["$id"], DRAFT202012.create_resource(document)) for document in documents.values() if isinstance(document.get("$id"), str)]
        + [(OPENAPI_URI, Resource(contents=openapi, specification=DRAFT202012))]
    )

    def validator_at(tokens):
        return Draft202012Validator({"$ref": OPENAPI_URI + "#" + pointer_of(tokens)}, registry=registry)

    counted = 0

    def validate(tokens, value, at):
        nonlocal counted
        counted += 1
        try:
            errors = sorted(validator_at(tokens).iter_errors(value), key=lambda error: error.json_path)
        except Exception as error:
            report.fail(where, "%s cannot be validated against: %s" % (at, error))
            return
        if errors:
            report.fail(where, "%s does not validate: %s at %s" % (at, errors[0].message, errors[0].json_path))

    for found in declared_in(openapi):
        node = found.node
        if found.kind in ("parameter", "header", "mediaType") and isinstance(node.get("examples"), dict) and "schema" in node:
            for name, example in node["examples"].items():
                example = followed(example, openapi)
                if isinstance(example, dict) and "value" in example:
                    validate(found.tokens + ("schema",), example["value"], "%s/examples/%s" % (found.where, name))
        if found.kind == "schema" and isinstance(node, dict):
            for inner in walk(node):
                examples = inner.schema.get("examples")
                if not isinstance(examples, list):
                    continue
                inner_tokens = found.tokens + tuple(inner.pointer.split("/")[1:])
                for index, example in enumerate(examples):
                    validate(inner_tokens, example, "%s%s/examples/%d" % (found.where, inner.pointer, index))

    report.heading("%s: %d examples, each valid against what it illustrates" % (where, counted))


# --------------------------------------------------------------------------------------
# The documentation's route table
#
# The documentation decides which routes exist, and the table at #api is where it lists
# them. This document follows it: a route the table lists and the document does not
# describe is either work not done or work deliberately not done yet, and the difference is
# written down in NOT_DESCRIBED_YET rather than left to whoever notices.
# --------------------------------------------------------------------------------------

# Where the documentation is read from when --docs does not say: the documentation of main,
# which the site serves at /docs/v/main/, rather than of the last release, which /docs
# serves. This repository's main describes what is being built, and the documentation
# decides that first, so the two mains are what have to agree.
DOCS_URL = "https://agentiik.github.io/docs/v/main/"

# The routes of the documentation's table this document does not describe yet, each group
# with the reason. A route listed here and described anyway, or listed here and gone from
# the table, fails too: this list is kept exact, so that it never hides a route by habit.
NOT_DESCRIBED_YET = (
    (
        "a phone's device and notification preferences, which the roadmap serves with the mobile applications in v1.0.0",
        (
            "POST /api/v1/me/devices",
            "PUT /api/v1/me/notifications",
        ),
    ),
    (
        "the runners, their pools and the bus, served since v0.2.0 and exchanged in the shapes wire.schema.json describes; no roadmap task adds them to this document yet",
        (
            "POST /api/v1/runners",
            "GET /api/v1/runners",
            "POST /api/v1/runners/{runner}/drain",
            "POST /api/v1/runners/{runner}/revoke",
            "POST /api/v1/runners/rotate",
            "POST /api/v1/runners/heartbeat",
            "POST /api/v1/bus/token",
            "GET /api/v1/runner-pools",
            "POST /api/v1/runner-pools",
            "POST /api/v1/runner-pools/{pool}/join-tokens",
            "POST /api/v1/tasks/redeem",
            "POST /api/v1/tasks/logs",
        ),
    ),
    (
        "secrets, workflows, their versions and the catalog; no roadmap task adds them to this document yet",
        (
            "GET /api/v1/{ns}/secrets",
            "GET /api/v1/{ns}/secrets/{name}",
            "PUT /api/v1/{ns}/secrets/{name}",
            "DELETE /api/v1/{ns}/secrets/{name}",
            "POST /api/v1/{ns}/workflows",
            "GET /api/v1/{ns}/workflows/{name}",
            "GET /api/v1/{ns}/workflows/{name}/tree/{ref}",
            "PUT /api/v1/{ns}/workflows/{name}/versions/{commit}",
            "GET /api/v1/bricks",
            "GET /api/v1/bricks/{name}",
        ),
    ),
    (
        "runs and their data; no roadmap task adds them to this document yet",
        (
            "POST /api/v1/{ns}/workflows/{name}/runs",
            "GET /api/v1/runs",
            "GET /api/v1/runs/{id}",
            "POST /api/v1/runs/{id}/cancel",
            "POST /api/v1/runs/{id}/approve",
            "POST /api/v1/runs/{id}/reject",
            "POST /api/v1/runs/{id}/replay",
            "GET /api/v1/runs/{id}/steps/{step}/logs",
            "GET /api/v1/runs/{id}/outputs/{name}",
            "GET /api/v1/runs/{id}/steps/{step}/outputs/{port}",
            "GET /api/v1/runs/{id}/steps/{step}/inputs/{port}",
            "GET /api/v1/artifacts/{uri}",
        ),
    ),
    (
        "the routes outside /api/v1 that carry no JSON: the object store, which a presigned URL or a signed policy authorises, git over smart HTTP, and webhooks",
        (
            "GET /objects/{key...}",
            "PUT /objects/{key...}",
            "POST /objects/{ns}",
            "GET /{ns}/{name}.git/*",
            "POST /{ns}/{name}.git/*",
            "POST /hooks/{ns}/{path}",
        ),
    ),
)

ROUTE_METHODS = ("GET", "PUT", "POST", "DELETE", "PATCH", "HEAD", "OPTIONS")
ROUTE_LINE = re.compile(r"^((?:%s)(?:,\s*(?:%s))*)\s+(\S.*)$" % ("|".join(ROUTE_METHODS), "|".join(ROUTE_METHODS)))


class RouteTable(HTMLParser):
    """The route table of the documentation's #api section, and every id on the page.

    The first table inside <section id="api"> is the route table; its first cell names one
    or more routes, a line each, and a row whose cells are headers is a group heading.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.state = "before"  # before, section, table, done
        self.rows = []
        self.row = None
        self.cell = None
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        if self.state == "before" and tag == "section" and attributes.get("id") == "api":
            self.state = "section"
        elif self.state == "section" and tag == "table":
            self.state = "table"
        elif self.state == "table":
            if tag == "tr":
                self.row = []
            elif tag in ("td", "th"):
                self.cell = {"header": tag == "th", "text": ""}
            elif tag == "br" and self.cell is not None:
                self.cell["text"] += "\n"

    def handle_endtag(self, tag):
        if self.state != "table":
            return
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            self.state = "done"

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"] += data


def routes_in_cell(text):
    """The routes one cell of the table names, and what could not be read in it.

    A cell holds a route a line: methods, then one or more paths. A path written after a
    comma continues the first one's /api/v1, as `GET /api/v1/bricks, /bricks/{name}` does,
    and a query string is not part of a route, which OpenAPI writes as parameters.
    """
    routes, unread = [], []
    for line in text.split("\n"):
        line = " ".join(line.split())
        if not line:
            continue
        match = ROUTE_LINE.match(line)
        if not match:
            unread.append(line)
            continue
        methods = [method.strip() for method in match.group(1).split(",")]
        paths = [path.strip() for path in match.group(2).split(",")]
        first = paths[0]
        for index, path in enumerate(paths):
            path = path.split("?", 1)[0]
            if not path.startswith("/") or " " in path:
                unread.append(line)
                break
            if index and first.startswith("/api/v1/") and not path.startswith("/api/v1/"):
                path = "/api/v1" + path
            routes.extend("%s %s" % (method, path) for method in methods)
    return routes, unread


def read_documentation(source):
    """The documentation's page, from a URL or a path; raises when it cannot be read."""
    if re.match(r"^https?://", source):
        request = urllib.request.Request(source, headers={"User-Agent": "agentiik-schemas-check"})
        with urllib.request.urlopen(request, timeout=30) as answer:
            return answer.read().decode("utf-8")
    path = Path(source)
    if path.is_dir():
        for candidate in (path / "docs" / "index.html", path / "index.html"):
            if candidate.is_file():
                path = candidate
                break
    return path.read_text(encoding="utf-8")


def check_routes_agree(openapi, source, report):
    """Check 10: the documentation's route table and the document list the same routes.

    A read that comes back partial is a failure, never an agreement: a page that could not
    be fetched, a page without the #api section, a table with no route, or a row this check
    cannot read. A tool that treats an empty read as nothing to do agrees with everything,
    which is the one answer this check exists not to give.
    """
    where = "the documentation"
    try:
        page = read_documentation(source)
    except Exception as error:
        report.fail(where, "cannot be read from %s (%s); the routes are not compared. Pass --docs with a checkout of agentiik.github.io to compare against one" % (source, error))
        return

    table = RouteTable()
    table.feed(page)
    if table.state == "before":
        report.fail(where, "%s has no <section id=\"api\">, so it is not the page listing the routes" % source)
        return
    if table.state == "section":
        report.fail(where, "the #api section of %s holds no table" % source)
        return

    listed = []
    for row in table.rows:
        if not row or row[0]["header"]:
            continue  # a group heading, or the table's own head
        routes, unread = routes_in_cell(row[0]["text"])
        for line in unread:
            report.fail(where, "the route table has a row this check cannot read: %r" % line)
        listed.extend(routes)
    if not listed:
        report.fail(where, "the route table of %s lists no route this check can read" % source)
        return

    documented = set(listed)
    described = {"%s %s" % (method.upper(), path) for path, method, _, _ in operations_of(openapi)}
    deferred = {}
    for reason, routes in NOT_DESCRIBED_YET:
        for route in routes:
            deferred[route] = reason

    for route in sorted(documented - described - set(deferred)):
        report.fail(where, "lists %s, which %s does not describe; describe it, or name it in NOT_DESCRIBED_YET with the reason" % (route, OPENAPI))
    for route in sorted(described - documented):
        report.fail(OPENAPI, "describes %s, which the documentation's route table does not list" % route)
    for route in sorted(set(deferred) & described):
        report.fail("tools/check.py", "NOT_DESCRIBED_YET names %s, which %s now describes; take it off the list" % (route, OPENAPI))
    for route in sorted(set(deferred) - documented):
        report.fail("tools/check.py", "NOT_DESCRIBED_YET names %s, which the documentation's route table no longer lists" % route)

    # Every operation says which section specifies it, and that section is on the page.
    for path, method, _, operation in operations_of(openapi):
        url = str((operation.get("externalDocs") or {}).get("url", ""))
        if url.startswith(DOCS_ANCHOR_PREFIX) and url[len(DOCS_ANCHOR_PREFIX):] not in table.ids:
            report.fail(OPENAPI, "%s points at %s, an anchor the documentation does not carry" % (readable(("paths", path, method)), url))

    report.heading(
        "the documentation lists %d routes: %d described here, %d not yet, as NOT_DESCRIBED_YET says why"
        % (len(documented), len(documented & described), len(documented & set(deferred)))
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="name every fixture, and say why each refused one was refused",
    )
    parser.add_argument(
        "--docs",
        default=DOCS_URL,
        metavar="SOURCE",
        help="where check 10 reads the documentation's route table: a URL, the page itself, or a checkout of agentiik.github.io (default: %(default)s)",
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

    # The OpenAPI document is read beside the schemas rather than among them: it is not a
    # schema, and it refers into them.
    openapi = None
    try:
        openapi = json.loads((ROOT / OPENAPI).read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.fail(OPENAPI, "is missing")
    except json.JSONDecodeError as error:
        report.fail(OPENAPI, "is not valid JSON: %s" % error)

    sound = {}
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
    if documents or openapi is not None:
        print("Patterns")
        check_every_pattern_is_portable(dict(documents, **({OPENAPI: openapi} if openapi is not None else {})), report)
    if documents:
        print("Grammars")
        check_every_copy_agrees(documents, report)
    if openapi is not None:
        print("OpenAPI")
        usable = check_openapi_is_sound(openapi, documents, report)
        check_openapi_is_documented(openapi, report)
        if usable:
            check_openapi_examples_validate(openapi, sound, report)
        print("Routes")
        check_routes_agree(openapi, arguments.docs, report)
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
