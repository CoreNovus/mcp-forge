"""Adapter utility for using objects that match a provider interface without subclassing.

For the rare case where you have an existing class that implements all the right methods
but doesn't inherit from the Base provider ABC.

Example::

    from mcp_forge_core.providers import adapt, BaseCacheProvider

    adapted = adapt(my_existing_cache, BaseCacheProvider)
"""

from __future__ import annotations

from abc import ABC
from typing import TypeVar

T = TypeVar("T", bound=ABC)


def adapt(obj: object, base_class: type[T]) -> T:
    """Verify that *obj* has all abstract methods of *base_class* and return it typed.

    This performs a runtime check that the object implements the required interface
    without requiring inheritance. Raises TypeError if any abstract method is missing
    or has an incompatible signature (wrong number of parameters).

    Args:
        obj: The object to adapt.
        base_class: The ABC base class whose interface must be satisfied.

    Returns:
        The same object, cast to the base class type.

    Raises:
        TypeError: If the object is missing required methods.
    """
    missing = []
    for name in _get_abstract_methods(base_class):
        attr = getattr(obj, name, None)
        if attr is None:
            missing.append(name)
        elif callable(getattr(base_class, name)) and not callable(attr):
            missing.append(f"{name} (not callable)")

    if missing:
        cls_name = type(obj).__name__
        base_name = base_class.__name__
        methods = ", ".join(missing)
        raise TypeError(
            f"Cannot adapt {cls_name} to {base_name}: missing methods: {methods}"
        )

    return obj  # type: ignore[return-value]


def _get_abstract_methods(cls: type) -> set[str]:
    """Extract the set of abstract method names from an ABC."""
    abstract = set()
    for name in dir(cls):
        method = getattr(cls, name, None)
        if getattr(method, "__isabstractmethod__", False):
            abstract.add(name)
    return abstract
