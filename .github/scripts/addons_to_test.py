#!/usr/bin/env python3
"""Print the addons a pull request needs to test, comma separated.

That is the addons it touches plus every addon in this repository that
depends on one of them, directly or not: changing ``l10n_ro_declaration``
has to re-run ``l10n_ro_declaration_D406``'s tests too.

Printing nothing means "test everything", and that is the answer whenever a
change lands outside an addon -- the workflow, the coverage configuration,
requirements -- because such a change can affect any of them.

Usage: addons_to_test.py <base-ref> <head-ref>

Only the test selection is narrowed. The database still gets every addon
installed: a module's tests can depend on data another module loads, which
no amount of reading the source reveals -- installing just l10n_ro_excise
and what its tests import still left its picking tests failing on a NOT NULL
column.
"""

import ast
import fnmatch
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Fisiere care nu pot schimba comportamentul, deci nu largesc selectia.
# Fara ele, orice pull request pierdea ingustarea: pre-commit regenereaza
# README-ul din radacina la fiecare bump de versiune, iar un fisier din afara
# unui modul inseamna "ruleaza tot".
INERT = (
    "README.md",
    "README.rst",
    "*/README.rst",
    "*/readme/*",
    "*/readme/*/*",
    "*/static/description/*",
    "*/static/description/*/*",
    "*/i18n/*.po",
    "*/i18n/*.pot",
)


def is_inert(path):
    return any(fnmatch.fnmatch(path, pattern) for pattern in INERT)


def local_addons():
    """``{addon: {direct dependencies}}`` for the addons in this repository.

    Addons flagged ``installable: False`` are left out: they cannot be given
    to ``-u``, and nothing installable is allowed to depend on them.
    """
    addons = {}
    for manifest in ROOT.glob("*/__manifest__.py"):
        try:
            data = ast.literal_eval(manifest.read_text())
        except (SyntaxError, ValueError):
            continue
        if not data.get("installable", True):
            continue
        addons[manifest.parent.name] = set(data.get("depends") or ())
    return addons


def changed_files(base, head):
    """The paths the pull request touches, or ``None`` if git cannot say.

    ``None`` is not a failure to report: it means the selection could not be
    narrowed, and the caller falls back to testing everything.
    """
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        print(out.stderr.strip(), file=sys.stderr)
        return None
    return [line for line in out.stdout.splitlines() if line]


def main(base, head):
    addons = local_addons()
    paths = changed_files(base, head)
    if paths is None:
        return ""

    touched = set()
    for path in paths:
        if is_inert(path):
            continue
        top = path.split("/", 1)[0]
        if top in addons:
            touched.add(top)
        elif (ROOT / top / "__manifest__.py").exists():
            # A non-installable addon: nothing to test, and nothing depends
            # on it either.
            continue
        else:
            # Not addon code: the change could reach anything.
            return ""

    if not touched:
        return ""

    # Walk the dependency graph backwards until it stops growing.
    selected = set(touched)
    while True:
        extra = {
            addon
            for addon, depends in addons.items()
            if addon not in selected and depends & selected
        }
        if not extra:
            break
        selected |= extra

    return ",".join(sorted(selected))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    print(main(sys.argv[1], sys.argv[2]))
