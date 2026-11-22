#!/usr/bin/env python3
"""Print the addons one CI shard has to test, comma separated.

Usage: shard_addons.py <shard index> <shard count> [--closure]

With ``--closure`` it prints the shard's addons plus every addon of this
repository they depend on, directly or not. That list is installed in ONE
``-i`` together with the tests, and ``--test-tags`` keeps only the shard's own
tests. Installing a dependency earlier (oca_init_test_database installs the
dependencies of ``INCLUDE``) would pull in shard addons too, and an addon that
is already installed does not run its tests: l10n_ro_config lost them that way.

The addons are the ``INCLUDE`` list from addons_to_test.py, or every
installable addon of the repository when it is empty. They are spread over
the shards by their test time (``test_weights.json``, seconds measured on a
full run; unknown addons count 10), longest first onto the lightest shard,
so the shards end at about the same time.

An empty line means this shard has nothing to test. It must not be passed
on as ``INCLUDE``: oca-ci reads an empty ``INCLUDE`` as "test everything".
"""

import ast
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEIGHT = 10


def installable_addons():
    """``{addon: {direct dependencies}}`` for the installable addons here."""
    addons = {}
    for manifest in ROOT.glob("*/__manifest__.py"):
        try:
            data = ast.literal_eval(manifest.read_text())
        except (SyntaxError, ValueError):
            continue
        if data.get("installable", True):
            addons[manifest.parent.name] = set(data.get("depends") or ())
    return addons


def closure(selected, addons):
    """``selected`` plus the repository addons they depend on, transitively."""
    result = set(selected)
    todo = list(selected)
    while todo:
        for dep in addons.get(todo.pop(), ()):
            if dep in addons and dep not in result:
                result.add(dep)
                todo.append(dep)
    return result


def main(index, count, with_closure=False):
    repo = installable_addons()
    include = os.environ.get("INCLUDE", "")
    addons = [a for a in include.split(",") if a] or list(repo)
    weights = json.loads((Path(__file__).parent / "test_weights.json").read_text())
    shards = [[0, []] for _ in range(count)]
    for addon in sorted(addons, key=lambda a: (-weights.get(a, DEFAULT_WEIGHT), a)):
        lightest = min(shards, key=lambda s: s[0])
        lightest[0] += weights.get(addon, DEFAULT_WEIGHT)
        lightest[1].append(addon)
    selected = shards[index][1]
    if with_closure and selected:
        selected = closure(selected, repo)
    return ",".join(sorted(selected))


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4) or sys.argv[3:] not in ([], ["--closure"]):
        sys.exit(__doc__)
    print(main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3:] == ["--closure"]))
