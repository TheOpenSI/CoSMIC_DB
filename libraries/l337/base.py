### Core modules ###
from abc import (
    ABC,
    abstractmethod
)
from re import (
    Pattern,
    compile
)
from unicodedata import normalize as unicode_normalize


### Type hints ###
from collections.abc import Sequence



"""
Foundation of the L337 matcher library.

Holds the matcher contract and the canonicalisation primitives shared by every
matching strategy. Concrete strategies live in `matcher.py`, keeping this
module free of API-specific and strategy-specific concerns so any API can build
on top of it.
"""


# Bound the work performed on attacker-controlled input (DB column caps the
# value at 100 characters anyway).
MAX_CANDIDATE_LENGTH: int = 128

# Invisible/format characters often abused to break up a keyword
_INVISIBLE_CHARS_PATTERN: Pattern[str] = compile(
    pattern=r'[\u200b-\u200f\u202a-\u202e\u2060\ufeff]'
)
# Any run of non-alphanumeric characters is a single separator
_NON_ALNUM_RUN_PATTERN: Pattern[str] = compile(pattern=r'[^a-z0-9]+')
# Canonical form with every separator removed
_NON_ALNUM_PATTERN: Pattern[str] = compile(pattern=r'[^a-z0-9]')


def clean_candidate(candidate: str) -> str:
    """Fold, strip invisible characters, lowercase and bound an input value."""
    folded: str = unicode_normalize(
        "NFKC",
        str(candidate)
    )
    visible: str = _INVISIBLE_CHARS_PATTERN.sub(
        "",
        folded
    )

    return visible.lower()[:MAX_CANDIDATE_LENGTH]


def canonicalise_separated(candidate: str) -> str:
    """Canonical form that keeps word boundaries as single underscores."""
    collapsed: str = _NON_ALNUM_RUN_PATTERN.sub(
        "_",
        clean_candidate(candidate)
    )

    return collapsed.strip("_")


def canonicalise_flat(candidate: str) -> str:
    """Canonical form with every non-alphanumeric character removed."""
    return _NON_ALNUM_PATTERN.sub(
        "",
        clean_candidate(candidate)
    )


class ImmutableFieldMatcher(ABC):
    """One strategy for deciding whether a candidate mimics a reserved value."""

    @abstractmethod
    def matches(
        self,
        candidate: str,
        reserved: Sequence[str]
    ) -> str | None:
        """
        Return the reserved value that `candidate` mimics, otherwise None.

        Args:
            candidate: Incoming, untrusted field value.
            reserved: Values that must not be mimicked.

        Returns:
            The first reserved value matched, or None when nothing matched.
        """
