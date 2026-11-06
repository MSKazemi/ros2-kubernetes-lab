"""Shared helpers for the tests (stdlib unittest only)."""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fixture_gen as fg  # noqa: E402
import handoff_sim as hs  # noqa: E402
import mission_state as ms  # noqa: E402
import validate_bundle as vb  # noqa: E402

BUNDLES = sorted((ROOT / "fixtures" / "bundles").glob("*.json"))
SCRIPTS = sorted((ROOT / "fixtures" / "scripts").glob("*.json"))


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def valid_pair():
    """A fresh (bundle, CommitContext) pair that is accepted."""
    bundle, ctx = fg.base_bundle(), fg.base_context()
    return copy.deepcopy(bundle), ms.CommitContext.from_json(ctx)


def make_sim(**kw):
    return hs.simulator_from_setup(fg.setup(**kw))
