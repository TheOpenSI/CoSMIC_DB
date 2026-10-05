### Core modules ###
from functools import lru_cache
from re import (
    IGNORECASE,
    Pattern,
    compile,
    escape
)
from rapidfuzz import fuzz


### Type hints ###
from collections.abc import Sequence
from typing import (
    Final,
    override
)


### Internal modules ###
from .base import (
    FUZZY_PARTIAL_RATIO_MIN_LEN,
    FUZZY_PARTIAL_RATIO_THRESHOLD,
    FUZZY_RATIO_THRESHOLD,
    ImmutableFieldMatcher,
    canonicalise_flat,
    canonicalise_separated,
    clean_candidate
)


"""
CoSMIC variant of L337 matcher library.


Every strategy satisfies the abstracted contract so that an API validator can
compose, reorder or drop them without changing its own logic.

The simpler strategies (exact, filler) live alongside the L337 strategies
(leet regex, fuzzy) so the whole set can be treated as one custom library.

L337 handling cannot enumerate every reading of an ambiguous substitution
(e.g., whether `1` means `i` or `l`), so two complementary strategies are
provided:

1. ImmutableFieldLeetRegexMatcher
- This matcher builds a per-reserved-value pattern where each letter accepts its
  known stand-ins, catching injections at the start, middle or end of a value.

2. ImmutableFieldFuzzyMatcher:
- This matcher normalises substitutions to their most common letter and falls
  back to `rapidfuzz` similarity for near-misses we did not anticipate.
"""


# Junk (digits/symbols) allowed between expected letters
_LEET_GAP_PATTERN: str = r'[^a-z]*'

# Characters that may stand in for a letter (single-word & multi-word cases)
_LEET_CHAR_CLASSES: dict[str, str] = {
    "a": "a4@",
    "b": "b8",
    "e": "e3",
    "g": "g69",
    "i": "i1l!|",
    "l": "l1|",
    "o": "o0",
    "s": "s5$",
    "t": "t7+",
    "z": "z2"
}

# Ambiguous readings resolved to their most common letter, used only by the
# near-miss (fuzzy) strategy to normalise both sides before comparison.
_LEET_TRANSLATION: dict[int, str] = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "2": "z",
        "3": "e",
        "4": "a",
        "5": "s",
        "6": "g",
        "7": "t",
        "8": "b",
        "9": "g",
        "@": "a",
        "$": "s",
        "!": "i",
        "|": "l",
        "+": "t"
    }
)


def de_leet(candidate: str) -> str:
    """Normalise common L337 substitutions to their plain letter reading."""
    return clean_candidate(candidate=candidate).translate(_LEET_TRANSLATION)


@lru_cache(maxsize=None)
def _leet_name_pattern(reserved_value: str) -> Pattern[str] | None:
    """Build (and cache) a full-match pattern accepting L337 variants."""
    flat_value: str = canonicalise_flat(candidate=reserved_value)

    if not flat_value:
        return None

    pattern_parts: list[str] = [_LEET_GAP_PATTERN]

    for character in flat_value:
        equivalents: str | None = _LEET_CHAR_CLASSES.get(
            character,
            None
        )

        if equivalents is None:
            pattern_parts.append(escape(pattern=character))

        else:
            pattern_parts.append(f"[{escape(pattern=equivalents)}]")

        pattern_parts.append(_LEET_GAP_PATTERN)

    return compile(
        pattern=r'^{pattern:s}$'.format(pattern="".join(pattern_parts)),
        flags=IGNORECASE
    )


class ImmutableFieldExactMatcher(ImmutableFieldMatcher):
    """Symbol/delimiter-only obfuscations with the letters left intact."""

    @override
    def matches(
        self,
        candidate:  str,
        reserved:   Sequence[str]
    ) -> str | None:
        candidate_separated:    str = canonicalise_separated(candidate=candidate)
        candidate_flat:         str = canonicalise_flat(candidate=candidate)

        if not candidate_flat:
            return None

        for reserved_value in reserved:
            if (
                candidate_separated
                and
                candidate_separated == canonicalise_separated(candidate=reserved_value)
            ):
                return reserved_value

            if candidate_flat == canonicalise_flat(candidate=reserved_value):
                return reserved_value

        return None


class ImmutableFieldLeetRegexMatcher(ImmutableFieldMatcher):
    """Number, symbol and L337 injections at start/middle/end of a value."""

    @override
    def matches(
        self,
        candidate:  str,
        reserved:   Sequence[str]
    ) -> str | None:
        cleaned: str = clean_candidate(candidate=candidate)

        if not cleaned:
            return None

        for reserved_value in reserved:
            pattern: Pattern[str] | None = _leet_name_pattern(reserved_value=reserved_value)

            if (
                pattern is not None
                and
                pattern.fullmatch(string=cleaned)
            ):
                return reserved_value

        return None


class ImmutableFieldFillerStripMatcher(ImmutableFieldMatcher):
    """Filler words injected around or in the middle of a reserved value."""

    def __init__(
        self,
        noises: Sequence[str]
    ) -> None:
        # Longest first (e.g. 'services' is stripped before 'service')
        self._noises: tuple[str, ...] = tuple(
            sorted(
                noises,
                key=len,
                reverse=True
            )
        )

    @override
    def matches(
        self,
        candidate:  str,
        reserved:   Sequence[str]
    ) -> str | None:
        cleaned: str = clean_candidate(candidate=candidate)

        for filler in self._noises:
            cleaned = cleaned.replace(
                filler,
                ""
            )

        separated: str = canonicalise_separated(candidate=cleaned)
        flat: str = canonicalise_flat(candidate=cleaned)

        if not flat:
            return None

        for reserved_value in reserved:
            if (
                separated
                and
                separated == canonicalise_separated(candidate=reserved_value)
            ):
                return reserved_value

            if flat == canonicalise_flat(candidate=reserved_value):
                return reserved_value

        return None


class ImmutableFieldFuzzyMatcher(ImmutableFieldMatcher):
    """Near-miss typos and containment that no deterministic rule enumerates."""

    def __init__(
        self,
        ratio_threshold:            int = FUZZY_RATIO_THRESHOLD,
        partial_ratio_threshold:    int = FUZZY_PARTIAL_RATIO_THRESHOLD,
        partial_ratio_min_len:      int = FUZZY_PARTIAL_RATIO_MIN_LEN
    ) -> None:
        self._ratio_threshold:          Final[int] = ratio_threshold
        self._partial_ratio_threshold:  Final[int] = partial_ratio_threshold
        self._partial_ratio_min_len:    Final[int] = partial_ratio_min_len

    @override
    def matches(
        self,
        candidate:  str,
        reserved:   Sequence[str]
    ) -> str | None:
        candidate_flat: str = canonicalise_flat(
            candidate=de_leet(
                candidate=candidate
            )
        )

        if not candidate_flat:
            return None

        for reserved_value in reserved:
            reserved_flat: str = canonicalise_flat(
                candidate=de_leet(
                    candidate=reserved_value
                )
            )

            if not reserved_flat:
                continue

            if fuzz.ratio(
                s1=candidate_flat,
                s2=reserved_flat
            ) >= self._ratio_threshold:
                return reserved_value

            # Containment only makes sense when the candidate can hold the
            # whole reserved value; otherwise it is just a short fragment
            if (
                len(candidate_flat) >= self._partial_ratio_min_len
                and
                fuzz.partial_ratio(
                    s1=candidate_flat,
                    s2=reserved_flat
                ) >= self._partial_ratio_threshold
            ):
                return reserved_value

        return None
