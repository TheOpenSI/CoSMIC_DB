### Core modules ###


### Type hints ###
from collections.abc import Sequence
from typing import override


### Internal modules ###
from .base import (
    ImmutableFieldMatcher,
    canonicalise_flat,
    canonicalise_separated,
    clean_candidate
)



"""
Concrete matching strategies of the L337 matcher library.

Every strategy satisfies the `ImmutableFieldMatcher` contract, so an API
validator can compose, reorder or drop them without changing its own logic.
The simpler strategies (exact, filler) live alongside the L337 strategies so
the whole set can be treated as one custom library.
"""


class ImmutableFieldExactMatcher(ImmutableFieldMatcher):
    """Symbol/delimiter-only obfuscations with the letters left intact."""

    @override
    def matches(
        self,
        candidate: str,
        reserved: Sequence[str]
    ) -> str | None:
        candidate_separated: str = canonicalise_separated(candidate)
        candidate_flat: str = canonicalise_flat(candidate)

        if not candidate_flat:
            return None

        for reserved_value in reserved:
            if (
                candidate_separated
                and candidate_separated == canonicalise_separated(reserved_value)
            ):
                return reserved_value

            if candidate_flat == canonicalise_flat(reserved_value):
                return reserved_value

        return None


class ImmutableFieldFillerStripMatcher(ImmutableFieldMatcher):
    """Filler words injected around or in the middle of a reserved value."""

    def __init__(self, noise_tokens: Sequence[str]) -> None:
        # Longest first so e.g. 'services' is stripped before 'service'
        self._noise_tokens: tuple[str, ...] = tuple(
            sorted(
                noise_tokens,
                key=len,
                reverse=True
            )
        )

    @override
    def matches(
        self,
        candidate: str,
        reserved: Sequence[str]
    ) -> str | None:
        cleaned: str = clean_candidate(candidate)

        for filler in self._noise_tokens:
            cleaned = cleaned.replace(filler, "")

        separated: str = canonicalise_separated(cleaned)
        flat: str = canonicalise_flat(cleaned)

        if not flat:
            return None

        for reserved_value in reserved:
            if separated and separated == canonicalise_separated(reserved_value):
                return reserved_value

            if flat == canonicalise_flat(reserved_value):
                return reserved_value

        return None
