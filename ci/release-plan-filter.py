"""Prints the manifest files whose change since a tag is more than metadata.

Usage: release-plan-filter.py <repository> <tag> <file> [<file> ...]

Each file is a pyproject.toml, setup.py or setup.cfg, as a path from the
repository root. Its text at the tag and at HEAD is compared with the
description, keywords, urls, classifiers, readme and authors left out, so a
file is printed when anything else changed, and left out when only those
did. A file that is missing on either side, or that cannot be read as what
its name says, is printed, so a release is never skipped by mistake.

Only the standard library is used, and the same way on every Python this
repository supports, so every job of a publish works out the same plan.
"""

import ast
import configparser
import os
import re
import subprocess
import sys

# The setup() arguments and setup.cfg [metadata] options that are metadata.
SETUP_METADATA = frozenset((
    "description", "long_description", "long_description_content_type",
    "keywords", "url", "project_urls", "download_url", "classifiers",
    "author", "author_email"))

# The pyproject.toml [project] keys that are metadata.
PROJECT_METADATA = frozenset((
    "description", "keywords", "urls", "classifiers", "readme", "authors"))

# A table header, such as [project.urls] or [[project.authors]].
HEADER = re.compile(r"^\[\[?\s*([^\]]+?)\s*\]\]?\s*(#.*)?$")

# The start of a key and value. The first part of a dotted key is the one
# that says what it is, as urls in urls.Homepage.
ASSIGNMENT = re.compile(
    r"^(\"[^\"]*\"|'[^']*'|[A-Za-z0-9_-]+)"
    r"(?:\s*\.\s*(?:\"[^\"]*\"|'[^']*'|[A-Za-z0-9_-]+))*\s*=")


def bytes_at(repository, revision, path):
    """The file's content at the revision, or None when it is not there."""
    found = subprocess.run(
        ["git", "-C", repository, "show", revision + ":" + path],
        capture_output=True)
    if found.returncode != 0:
        return None
    return found.stdout


class StripSetupMetadata(ast.NodeTransformer):
    """Removes the metadata arguments from every call of setup()."""

    def visit_Call(self, node):
        self.generic_visit(node)
        name = node.func.attr if isinstance(node.func, ast.Attribute) \
            else getattr(node.func, "id", None)
        if name == "setup":
            node.keywords = [
                keyword for keyword in node.keywords
                if keyword.arg not in SETUP_METADATA]
        return node


def setup_py(text):
    # The syntax tree leaves out comments and layout as well.
    return ast.dump(StripSetupMetadata().visit(ast.parse(text)))


def setup_cfg(text):
    parser = configparser.RawConfigParser()
    parser.optionxform = str
    parser.read_string(text)
    return {
        section: {
            key: value for key, value in parser.items(section)
            if section != "metadata" or key not in SETUP_METADATA}
        for section in parser.sections()}


def toml_lines(text):
    """The lines of a TOML file that are not metadata, each with the table
    and key it belongs to, leaving out blank lines and comments.

    A small reader rather than tomllib, which Python 3.10 does not have. It
    follows tables, keys, values that run over several lines in brackets or
    in triple quotes, and comments, which is enough to place every line.
    """
    kept = []
    table = ""
    key = None
    depth = 0
    quote = None
    for line in text.splitlines():
        stripped = line.strip()
        if quote is None and depth == 0:
            if stripped == "" or stripped.startswith("#"):
                continue
            header = HEADER.match(stripped)
            if header:
                table = header.group(1).replace(" ", "")
                key = None
                if not is_metadata(table, None):
                    kept.append((table, None, stripped))
                continue
            assignment = ASSIGNMENT.match(stripped)
            if assignment is None:
                # Not TOML this reader knows, so it counts unless the whole
                # table is metadata.
                if not is_metadata(table, "?"):
                    kept.append((table, "?", stripped))
                continue
            key = assignment.group(1).strip("\"'")
            value = stripped[assignment.end():]
        else:
            value = stripped
        depth, quote = scan(value, depth, quote)
        if not is_metadata(table, key):
            kept.append((table, key, stripped))
    return kept


def scan(value, depth, quote):
    """The bracket depth and the open triple quote after the value."""
    position = 0
    while position < len(value):
        if quote is not None:
            end = value.find(quote, position)
            if end < 0:
                return depth, quote
            position = end + 3
            quote = None
            continue
        character = value[position]
        if value.startswith('"""', position) or \
                value.startswith("'''", position):
            quote = value[position:position + 3]
            position += 3
            continue
        if character in "\"'":
            end = value.find(character, position + 1)
            position = len(value) if end < 0 else end + 1
            continue
        if character == "#":
            break
        if character in "[{":
            depth += 1
        elif character in "]}":
            depth -= 1
        position += 1
    return depth, quote


def is_metadata(table, key):
    if table == "project":
        return key in PROJECT_METADATA
    return table in ("project.urls", "project.authors", "project.readme")


READERS = {
    "setup.py": setup_py,
    "setup.cfg": setup_cfg,
    "pyproject.toml": toml_lines,
}


def counts(repository, tag, path):
    """Whether the change to the file since the tag is more than metadata."""
    reader = READERS.get(os.path.basename(path))
    before = bytes_at(repository, tag, path)
    after = bytes_at(repository, "HEAD", path)
    if reader is None or before is None or after is None:
        return True
    try:
        return reader(before.decode("utf-8")) != reader(after.decode("utf-8"))
    except (SyntaxError, ValueError, configparser.Error,
            UnicodeDecodeError):
        return True


def main(arguments):
    repository, tag = arguments[0], arguments[1]
    for path in arguments[2:]:
        if counts(repository, tag, path):
            print(path)


if __name__ == "__main__":
    main(sys.argv[1:])
