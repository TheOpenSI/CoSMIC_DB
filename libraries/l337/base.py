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
CoSMIC variant of L337 matcher library.


I tried to find around if there're any industry standard libraries that handle
this. However, most of them only helps converting any inputs into L337 style
input but not vice versa. This library holds the matcher contract and the
canonicalisation primitives shared by every matching strategy. Concrete
strategies live in `matcher.py`, keeping this module free of API-specific and
strategy-specific concerns so any API can build on top of it.
"""


# Similarity policy for catching near-miss (e.g., L337) immutable fields mimicry.
# For example, a single edit on a short core service name (e.g., 'chess') dips
# well below these values, so a low bar here still keeps distinct, unrelated
# names allowed
FUZZY_RATIO_THRESHOLD: int = 85
FUZZY_PARTIAL_RATIO_THRESHOLD: int = 90

# Partial ratio only searches for a reserved value inside the candidate, so a
# candidate shorter than the shortest supported reserved value is a fragment
# rather than a containment. Gating it keeps stray short fragments (e.g. `h`
# left after non-Latin characters are stripped) from being rejected, while
# the ratio still covers genuine near-misses
FUZZY_PARTIAL_RATIO_MIN_LEN: int = 5

# Bound the work performed on attacker-controlled input (DB column caps the
# value at 100 characters anyway)
MAX_CANDIDATE_LEN: int = 128

# Invisible characters format often abused to break up a keyword
_INVIS_CHARS_PATTERN: Pattern[str] = compile(
    pattern=r'[\u200b-\u200f\u202a-\u202e\u2060\ufeff]',
    flags=0
)

# Any run of non-alphanumeric characters is a single separator
_NON_ALNUM_RUN_PATTERN: Pattern[str] = compile(
    pattern=r'[^a-z0-9]+',
    flags=0
)
# Canonical form with every separator removed
_NON_ALNUM_PATTERN: Pattern[str] = compile(
    pattern=r'[^a-z0-9]',
    flags=0
)


def clean_candidate(candidate: str) -> str:
    """Fold, strip invisible characters, lowercase and bound an input value."""
    folded: str = unicode_normalize(
        "NFKC",
        str(candidate)
    )
    visible: str = _INVIS_CHARS_PATTERN.sub(
        repl="",
        string=folded,
        count=0
    )

    return visible.lower()[:MAX_CANDIDATE_LEN]


def canonicalise_separated(candidate: str) -> str:
    """Canonical form that keeps word boundaries as single underscores."""
    collapsed: str = _NON_ALNUM_RUN_PATTERN.sub(
        repl="_",
        string=clean_candidate(candidate),
        count=0
    )

    return collapsed.strip("_")


def canonicalise_flat(candidate: str) -> str:
    """Canonical form with every non-alphanumeric character removed."""
    return _NON_ALNUM_PATTERN.sub(
        repl="",
        string=clean_candidate(candidate),
        count=0
    )


class ImmutableFieldMatcher(ABC):
    """One strategy for deciding whether a candidate mimics a reserved value."""

    @abstractmethod
    def matches(
        self,
        candidate:  str,
        reserved:   Sequence[str]
    ) -> str | None:
        """
        Return the reserved value that candidate mimics, otherwise None.

        Args:
            candidate:
                incoming, untrusted field value.

            reserved:
                values that must not be mimicked.

        Returns:
            The first reserved value matched, or None when nothing matched.
        """
