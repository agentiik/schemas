#!/usr/bin/env python3
"""Generates the language reference from the workflow schema.

Run it with no arguments, from anywhere, after changing a schema:

    python tools/language.py

It writes language/, which is generated and never edited by hand:

  language/index.md      the orientation a client reads first: what the language is, one
                         complete minimal workflow, the topics and the schema parts;
  language/<topic>.md    one page per topic: a summary, its keywords, the schema fragment
                         governing them and worked examples, each placed where it is written
                         in agentiik.yaml;
  language/topics.json   the same topics for a program: which keywords each one covers, the
                         instance paths it answers for, and the schema parts by name.

The documentation decides that the language is taught from the schema and never beside it:
"workflow.language projects the description and examples of every keyword in the JSON Schema
of agentiik/schemas, and the build fails if a keyword lacks them. Two hand-kept sources would
drift, into the worst failure available: a tool confidently teaching a model syntax the
pre-receive hook then rejects." So every sentence on a page is a description field of a
schema, and every example an entry of an examples array. What this file adds is structure
alone: which keyword belongs to which topic, and the order a page is read in.

tools/check.py regenerates the directory in memory and fails when the committed one differs,
so a schema change that forgets to run this is caught by the build rather than by a client.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "language"
WORKFLOW = "workflow.schema.json"

# The schema parts a client can ask for by name: workflow.schema and agentiik://schema/{part}
# take one of these. A part is named after its file, so the name, the file and the $id say
# the same thing and none of them needs a table to be found from another; what a part is, the
# index takes from the part's own title and description. The documentation names these
# three: "the entry point, a brick manifest or an envelope".
PARTS = (
    ("workflow", "workflow.schema.json"),
    ("brick", "brick.schema.json"),
    ("envelope", "envelope.schema.json"),
)

# The topics, in the order the documentation lists them: "repository, inputs, outputs,
# triggers, steps, ports, needs, merge, fan_out, retry, expressions, secrets, files, script,
# includes, mcp". Each names the keyword whose description is its summary, and the places in
# workflow.schema.json it covers. A keyword belongs to the topic whose place is the longest
# prefix of where the keyword is declared, so steps can cover the step while retry takes the
# step's retry away from it. check.py fails when a keyword is covered by no topic, since a
# keyword no page teaches is one a client never learns.
TOPICS = (
    (
        "repository",
        "",
        (
            "/properties/apiVersion",
            "/properties/kind",
            "/properties/metadata",
            "/properties/concurrency",
            "/properties/timeout",
            "/properties/vars",
            "/$defs/vars",
            "/$defs/identifier",
            "/$defs/namespace",
            "/$defs/duration",
        ),
    ),
    ("inputs", "/properties/inputs", ("/properties/inputs", "/$defs/workflowInput", "/$defs/jsonSchema")),
    ("outputs", "/properties/outputs", ("/properties/outputs", "/$defs/workflowOutput", "/$defs/retainOutput", "/$defs/retain")),
    (
        "triggers",
        "/properties/on",
        ("/properties/on", "/$defs/scheduleTrigger", "/$defs/webhookTrigger", "/$defs/eventTrigger"),
    ),
    (
        "steps",
        "/properties/steps",
        (
            "/properties/steps",
            "/$defs/steps",
            "/$defs/step",
            "/$defs/paramName",
            "/$defs/timeout",
            "/$defs/resources",
            "/$defs/network",
            "/$defs/egress",
            "/$defs/runsOn",
            "/$defs/cache",
        ),
    ),
    ("ports", "/$defs/step/properties/outputs", ("/$defs/step/properties/inputs", "/$defs/step/properties/outputs", "/$defs/portName")),
    (
        "needs",
        "/$defs/step/properties/needs",
        ("/$defs/step/properties/needs", "/$defs/edge", "/$defs/step/properties/when", "/$defs/when", "/$defs/step/properties/if"),
    ),
    ("merge", "/$defs/step/properties/merge", ("/$defs/step/properties/merge",)),
    ("fan_out", "/$defs/step/properties/strategy", ("/$defs/step/properties/strategy",)),
    (
        "retry",
        "/$defs/retry",
        (
            "/$defs/step/properties/retry",
            "/$defs/retry",
            "/$defs/step/properties/continue_on_error",
            "/$defs/continueOnError",
            "/$defs/step/properties/idempotent",
            "/$defs/idempotent",
        ),
    ),
    ("expressions", "/$defs/expression", ("/$defs/expression",)),
    ("secrets", "/properties/secrets", ("/properties/secrets", "/$defs/secrets", "/$defs/step/properties/secrets", "/$defs/stepSecrets")),
    ("files", "/$defs/files", ("/$defs/step/properties/files", "/$defs/files")),
    (
        "script",
        "/$defs/step/properties/script",
        (
            "/$defs/step/properties/script",
            "/$defs/step/properties/before_script",
            "/$defs/step/properties/after_script",
            "/$defs/step/properties/shell",
            "/$defs/commands",
            "/$defs/beforeScript",
            "/$defs/afterScript",
            "/$defs/shell",
        ),
    ),
    (
        "includes",
        "/properties/include",
        (
            "/properties/include",
            "/$defs/includes",
            "/$defs/include",
            "/$defs/workflowPath",
            "/$defs/fragment",
            "/properties/defaults",
            "/$defs/defaults",
            "/$defs/step/properties/extends",
            "/patternProperties",
        ),
    ),
    ("mcp", "/properties/mcp", ("/properties/mcp", "/$defs/mcpTimeout", "/dependentSchemas/mcp")),
)

# Keywords the walk descends through, the same three families check.py walks. A keyword is
# an entry of properties, patternProperties or $defs; a subschema reached through not, if,
# then, else or dependentSchemas restates a keyword declared elsewhere and declares nothing.
MAP_OF_SUBSCHEMAS = ("properties", "patternProperties", "$defs", "dependentSchemas")
ONE_SUBSCHEMA = ("items", "contains", "additionalProperties", "propertyNames", "not", "if", "then", "else",
                 "unevaluatedItems", "unevaluatedProperties", "contentSchema")
LIST_OF_SUBSCHEMAS = ("allOf", "anyOf", "oneOf", "prefixItems")
CONSTRAINTS = ("not", "if", "then", "else", "dependentSchemas")

# What the schema fragment on a page leaves out, because the page says it already: the
# keywords list carries every description, and the examples section every example.
PROSE = ("title", "description", "examples", "$comment")


class Dumper(yaml.SafeDumper):
    """YAML as the engine reads it, which is YAML 1.2.

    YAML 1.1 reads on, off, yes and no as booleans, so a YAML 1.1 dumper quotes the key on
    to keep it a string. The language spells its trigger block on: and the engine reads
    YAML 1.2, where on is a string, so the pages write it bare, as an author does; check.py
    reads every page back with a YAML 1.2 loader to hold that.
    """


Dumper.yaml_implicit_resolvers = {
    first: [(tag, pattern) for tag, pattern in resolvers if not tag.endswith(":bool")]
    for first, resolvers in yaml.SafeDumper.yaml_implicit_resolvers.items()
}
Dumper.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def legible(text):
    """JSON text with every character a reader cannot see written as its escape. A pattern
    naming the spaces of every script holds them as characters, which a page showing them
    as they are would show as a run of blanks, and a line separator among them as a break."""
    return "".join(c if c.isprintable() else json.dumps(c)[1:-1] for c in text)


def render_json(value, indent=""):
    """JSON as a page shows it: a value on one line where it fits in 100 characters, and
    broken over lines only where it does not, so a fragment reads as the shape it is rather
    than as a column of brackets."""
    flat = legible(json.dumps(value, ensure_ascii=False))
    if len(indent) + len(flat) <= 100 or not isinstance(value, (dict, list)) or not value:
        return flat
    inner = indent + "  "
    if isinstance(value, dict):
        body = [inner + legible(json.dumps(key, ensure_ascii=False)) + ": " + render_json(item, inner).lstrip() for key, item in value.items()]
        return "{\n" + ",\n".join(body) + "\n" + indent + "}"
    body = [inner + render_json(item, inner).lstrip() for item in value]
    return "[\n" + ",\n".join(body) + "\n" + indent + "]"


def render_yaml(value):
    text = yaml.dump(value, Dumper=Dumper, sort_keys=False, default_flow_style=False, allow_unicode=True, width=4096)
    # A lone scalar is followed by the document end marker, which says nothing to an author
    # and reads the same without it.
    return text[: -len("...\n")] if text.endswith("\n...\n") else text


def walk(node, pointer="", name=None, constrained=False):
    """Yields (pointer, subschema, declares a keyword) for every subschema, root included."""
    if not isinstance(node, dict):
        return
    yield pointer, node, (name is not None and not constrained) or pointer == ""
    for keyword in MAP_OF_SUBSCHEMAS:
        entries = node.get(keyword)
        if isinstance(entries, dict):
            for entry, subschema in entries.items():
                yield from walk(subschema, "%s/%s/%s" % (pointer, keyword, entry), entry,
                                constrained or keyword in CONSTRAINTS)
    for keyword in ONE_SUBSCHEMA:
        subschema = node.get(keyword)
        if isinstance(subschema, dict):
            yield from walk(subschema, "%s/%s" % (pointer, keyword), None, constrained or keyword in CONSTRAINTS)
    for keyword in LIST_OF_SUBSCHEMAS:
        entries = node.get(keyword)
        if isinstance(entries, list):
            for index, subschema in enumerate(entries):
                yield from walk(subschema, "%s/%s/%d" % (pointer, keyword, index), None, constrained)


def at(document, pointer):
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


def placeholder(document, schema):
    """The name a worked example writes where the author chooses one: the first example of
    the keyword's propertyNames when it has one, so that a step is called normalize and an
    input orders rather than something no author would write."""
    names = schema.get("propertyNames")
    if isinstance(names, dict):
        for source in (names, at(document, names["$ref"]) if "$ref" in names else None):
            if isinstance(source, dict) and source.get("examples"):
                return str(source["examples"][0])
    for example in schema.get("examples") or []:
        if isinstance(example, dict) and example:
            return next(iter(example))
    return "name"


def instance_paths(document):
    """Where each keyword is written in a document, as instance paths.

    A path is a list of tokens, a token being a key the file writes or, where the author
    chooses the key or the index, a pair of the pattern that stands for it and the name or
    index a worked example writes there: ("*", "normalize") for a step, ("*", 0) for the
    first entry of a list, and (".*", ".base") for a hidden block at the root, whose name is
    any that starts with a dot. The walk
    starts at the root of the entry point and at $defs/fragment, the included file, and
    follows $ref, so a definition is found at every place a file can write it, in reading
    order: the first place is the one a worked example is shown at.
    """
    found = {}

    def visit(pointer, schema, path, trail):
        if not isinstance(schema, dict) or len(path) > 12:
            return
        key = (pointer, tuple(t if isinstance(t, str) else t[0] for t in path))
        if key in trail:
            return
        trail = trail | {key}
        found.setdefault(pointer, [])
        if path not in found[pointer]:
            found[pointer].append(path)
        reference = schema.get("$ref")
        if isinstance(reference, str) and reference.startswith("#"):
            visit(reference[1:], at(document, reference), path, trail)
        for keyword in ("allOf", "anyOf", "oneOf"):
            for index, branch in enumerate(schema.get(keyword) or []):
                visit("%s/%s/%d" % (pointer, keyword, index), branch, path, trail)
        for entry, subschema in (schema.get("properties") or {}).items():
            visit("%s/properties/%s" % (pointer, entry), subschema, path + [entry], trail)
        for entry, subschema in (schema.get("patternProperties") or {}).items():
            # A hidden block at the root has no propertyNames to take a name from, and its
            # pattern says only that the name starts with a dot.
            token = (".*", ".base") if entry.startswith("^\\.") else ("*", placeholder(document, schema))
            visit("%s/patternProperties/%s" % (pointer, entry), subschema, path + [token], trail)
        extra = schema.get("additionalProperties")
        if isinstance(extra, dict):
            visit(pointer + "/additionalProperties", extra, path + [("*", placeholder(document, schema))], trail)
        items = schema.get("items")
        if isinstance(items, dict):
            visit(pointer + "/items", items, path + [("*", 0)], trail)

    visit("", document, [], frozenset())
    fragment = at(document, "/$defs/fragment")
    if fragment is not None:
        visit("/$defs/fragment", fragment, [], frozenset())
    return found


def pattern_of(path):
    """An instance path as a JSON Pointer pattern, the pointer a validation error names with
    * for any one name or index and .* for any one name starting with a dot. The root is the
    empty pointer, as RFC 6901 writes it."""
    return "".join("/" + (t[0] if not isinstance(t, str) else t.replace("~", "~0").replace("/", "~1")) for t in path)


def placed(path, value):
    """The value written where the path says, the way an author writes it in the file."""
    for token in reversed(path):
        if isinstance(token, str):
            value = {token: value}
        elif isinstance(token[1], int):
            value = [value]
        else:
            value = {token[1]: value}
    return value


def owner_of(pointer, roots):
    """The topic whose place is the longest prefix of a keyword's declaration."""
    best, length = None, -1
    for topic, places in roots.items():
        for place in places:
            if (pointer == place or pointer.startswith(place + "/")) and len(place) > length:
                best, length = topic, len(place)
    return best


def stripped(schema, pointer, owners, topic):
    """A subschema as a page shows it: validation keywords only, and a keyword another topic
    teaches replaced by a note naming that topic, so a page shows what it governs."""
    if isinstance(schema, list):
        return [stripped(s, "%s/%d" % (pointer, i), owners, topic) for i, s in enumerate(schema)]
    if not isinstance(schema, dict):
        return schema
    out = {}
    for key, value in schema.items():
        if key in PROSE:
            continue
        if key in ("properties", "patternProperties", "$defs", "dependentSchemas") and isinstance(value, dict):
            entries = {}
            for entry, subschema in value.items():
                here = "%s/%s/%s" % (pointer, key, entry)
                other = owners.get(here)
                if other is not None and other != topic and key != "dependentSchemas":
                    entries[entry] = {"$comment": "taught by the %s topic" % other}
                else:
                    entries[entry] = stripped(subschema, here, owners, topic)
            out[key] = entries
        elif key in ONE_SUBSCHEMA:
            out[key] = stripped(value, "%s/%s" % (pointer, key), owners, topic)
        elif key in LIST_OF_SUBSCHEMAS:
            out[key] = [stripped(s, "%s/%s/%d" % (pointer, key, i), owners, topic) for i, s in enumerate(value)]
        else:
            out[key] = copy.deepcopy(value)
    return out


def first_sentence(text):
    match = re.match(r"(.+?[.!?])(\s|$)", text.strip())
    return match.group(1) if match else text.strip()


def reference(documents):
    """The whole reference from the schema documents, keyed by file name.

    Returns the files to write, as {name under language/: text}, and the worked examples as
    check.py holds them: each keyword, the example's index in its examples, the instance
    path it is placed at, the value and the YAML the page shows for it.
    """
    document = documents[WORKFLOW]
    roots = {name: places for name, _anchor, places in TOPICS}
    paths = instance_paths(document)

    keywords = [(pointer, schema) for pointer, schema, declares in walk(document) if declares]
    owners = {pointer: owner_of(pointer, roots) for pointer, _ in keywords}
    # The root is the document itself, and what it is is the repository topic's summary.
    owners[""] = "repository"

    files, worked = {}, []
    index = {"orientation": "index.md", "topics": [], "parts": []}

    for name, anchor, places in TOPICS:
        summary = at(document, anchor)["description"]
        # The anchor first, since its description is the summary the rest elaborates; then
        # the others in the order the schema declares them.
        mine = sorted(((p, s) for p, s in keywords if owners.get(p) == name), key=lambda k: k[0] != anchor)
        lines = ["# `%s`" % name, "", summary, "", "## Keywords", ""]
        topic_paths, examples = [], []
        for pointer, schema in mine:
            where = paths.get(pointer) or []
            patterns = []
            for path in where:
                if pattern_of(path) not in patterns:
                    patterns.append(pattern_of(path))
            # A place in topics.json is claimed by the keyword written there, and so by one
            # topic. A definition claims none: it is reached through a property that is written
            # there and answers for it, a duration being the retry topic's inside a retry and a
            # timeout's inside a step. Nor does a keyword of the included file, which restates
            # at the same place a keyword of the entry point. check.py holds every place to one
            # topic, so an error's topic never depends on the order topics are listed in.
            definition = re.fullmatch(r"/\$defs/[^/]+", pointer) is not None
            # A definition written at several places is a grammar several keywords share, an
            # expression being an event filter in one place and a step's if in another. Its
            # examples are shown as values rather than placed at the first of those places,
            # where they would teach a filter that reads an input. A keyword written at one
            # place, or declared inside a definition, is shown where it is written.
            shared = definition and len(patterns) > 1
            if not definition and not pointer.startswith("/$defs/fragment/"):
                for pattern in patterns:
                    if pattern not in topic_paths:
                        topic_paths.append(pattern)
            written = ", ".join("`%s`" % p for p in patterns) if patterns else "`%s#%s`" % (WORKFLOW, pointer)
            lines.append("- %s: %s" % (written, schema.get("description", "")))
            for i, example in enumerate(schema.get("examples") or []):
                if shared or not where:
                    examples.append((pointer, i, [], example))
                else:
                    examples.append((pointer, i, where[0], example))
        lines += ["", "## Schema", ""]
        for place in places:
            lines += ["`%s#%s`:" % (WORKFLOW, place), "", "```json",
                      render_json(stripped(at(document, place), place, owners, name)),
                      "```", ""]
        lines += ["## Examples", ""]
        shown = set()
        for pointer, i, path, value in examples:
            text = render_yaml(placed(path, value))
            worked.append({"topic": name, "keyword": pointer, "index": i, "path": path, "value": value, "yaml": text})
            if text in shown:
                continue
            shown.add(text)
            label = pattern_of(path) if path or pointer == "" else "%s#%s" % (WORKFLOW, pointer)
            lines += ["`%s`:" % (label or "agentiik.yaml"), "", "```yaml", text.rstrip("\n"), "```", ""]
        files["%s.md" % name] = "\n".join(lines).rstrip("\n") + "\n"
        index["topics"].append({
            "name": name,
            "page": "%s.md" % name,
            "summary": first_sentence(summary),
            "keywords": [p for p, _ in mine],
            "paths": topic_paths,
        })

    for name, filename in PARTS:
        part = documents[filename]
        index["parts"].append({
            "name": name,
            "file": filename,
            "$id": part["$id"],
            "title": part["title"],
            "summary": first_sentence(part["description"]),
        })

    # The first example of the root is the complete minimal workflow the orientation shows,
    # which is why it is the smallest workflow that runs: one step, no brick to pull, one output.
    lines = ["# %s" % document["title"], "", document["description"], "",
             "## A complete minimal workflow", "",
             "```yaml", render_yaml(document["examples"][0]).rstrip("\n"), "```", "",
             "## Topics", ""]
    for topic in index["topics"]:
        lines.append("- `%s`: %s" % (topic["name"], topic["summary"]))
    lines += ["", "## Schema parts", ""]
    for part in index["parts"]:
        lines.append("- `%s`, %s: %s `%s`" % (part["name"], part["title"], part["summary"], part["$id"]))
    files["index.md"] = "\n".join(lines) + "\n"
    files["topics.json"] = json.dumps(index, indent=2, ensure_ascii=False) + "\n"
    return files, worked, owners


def read_documents():
    return {filename: json.loads((ROOT / filename).read_text(encoding="utf-8")) for _, filename in PARTS}


def main():
    files, _, _ = reference(read_documents())
    OUT.mkdir(exist_ok=True)
    for stale in OUT.iterdir():
        if stale.name not in files:
            stale.unlink()
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8")
    print("wrote %d files under %s" % (len(files), OUT.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
