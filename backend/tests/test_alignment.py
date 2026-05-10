"""
Tests for the alignment service — Union-Find clustering and merge logic.

Run: python -m pytest backend/tests/test_alignment.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.services.alignment_service import UnionFind


def test_union_find_single_element():
    """Each element starts as its own root."""
    uf = UnionFind()
    assert uf.find("a") == "a"
    assert uf.find("b") == "b"


def test_union_find_merge_two():
    """Union merges two elements into the same set."""
    uf = UnionFind()
    uf.union("a", "b")
    assert uf.find("a") == uf.find("b")


def test_union_find_transitive():
    """Union is transitive: a-b and b-c implies a-c in same set."""
    uf = UnionFind()
    uf.union("a", "b")
    uf.union("b", "c")
    assert uf.find("a") == uf.find("c")


def test_union_find_no_merge_different_sets():
    """Disconnected pairs stay in different sets."""
    uf = UnionFind()
    uf.union("a", "b")
    uf.union("c", "d")
    assert uf.find("a") != uf.find("c")
    assert uf.find("b") != uf.find("d")


def test_union_find_rank_compression():
    """Path compression keeps roots consistent after multiple operations."""
    uf = UnionFind()
    uf.union("a", "b")
    uf.union("b", "c")
    uf.union("c", "d")
    root = uf.find("d")
    assert uf.find("a") == root
    assert uf.find("b") == root
    assert uf.find("c") == root


def test_union_find_idempotent():
    """Union of already-merged sets is idempotent."""
    uf = UnionFind()
    uf.union("a", "b")
    uf.union("a", "b")  # second time should not break anything
    assert uf.find("a") == uf.find("b")
