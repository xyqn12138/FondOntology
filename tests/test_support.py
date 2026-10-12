"""Suite-scoped read-only fixtures; mutation tests use the real build_stack."""
from pathlib import Path

from fondontology.qa.graph import build_stack
from fondontology.qa.engine import _get_index

_STACKS = {}


def shared_stack(source, abox=None, reasoner_profile="OWL-RL"):
    key = (Path(source).resolve(), Path(abox).resolve() if abox else None,
           reasoner_profile)
    if key not in _STACKS:
        _STACKS[key] = build_stack(*key)
    return _STACKS[key]


def shared_index(stack):
    return _get_index(stack)


def clear_shared_fixtures():
    _STACKS.clear()
