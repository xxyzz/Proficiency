import random
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Node:
    c: str = ""
    left: Optional["Node"] = None  # Python 3.11 can use typing.Self
    mid: Optional["Node"] = None
    right: Optional["Node"] = None
    val: Any = None


# Ternary search tries
class TST:
    def __init__(self) -> None:
        self.root: Node | None = None

    def get(self, key: str) -> Any:
        if not key:
            return None
        x = self.get_helper(self.root, key)
        return x.val if x else None

    def get_helper(self, x: Node | None, key: str) -> Node | None:
        if x is None:
            return None
        c = key[0]
        if c < x.c:
            return self.get_helper(x.left, key)
        elif c > x.c:
            return self.get_helper(x.right, key)
        elif len(key) > 1:
            return self.get_helper(x.mid, key[1:])
        else:
            return x

    def put(self, key: str, val: Any) -> None:
        if not key or not val:
            return None
        self.root = self.put_helper(self.root, key, val)

    def put_values(self, values: list[tuple[str, int]]) -> None:
        random.shuffle(values)
        for key, val in values:
            self.put(key, val)

    def put_helper(self, x: Node | None, key: str, val: Any) -> Node:
        c = key[0]
        if x is None:
            x = Node()
            x.c = c
        if c < x.c:
            x.left = self.put_helper(x.left, key, val)
        elif c > x.c:
            x.right = self.put_helper(x.right, key, val)
        elif len(key) > 1:
            x.mid = self.put_helper(x.mid, key[1:], val)
        else:
            x.val = val
        return x

    def get_prefix(self, pre: str) -> Any:
        if not pre:
            return None
        return self.get_prefix_helper(self.get_helper(self.root, pre))

    def get_prefix_helper(self, x: Node | None) -> Any:
        if x is None:
            return None
        if x.val:
            return x.val
        node = self.get_prefix_helper(x.mid)
        if node is None:
            node = self.get_prefix_helper(x.left)
        if node is None:
            node = self.get_prefix_helper(x.right)
        return node
