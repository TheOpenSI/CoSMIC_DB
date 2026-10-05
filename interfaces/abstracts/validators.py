### Core modules ###
from abc import (
    ABC,
    abstractmethod
)


### Type hints ###
from collections.abc import Sequence
from typing import ClassVar


### Internal modules ###
from ...libraries.l337.base import ImmutableFieldMatcher


class ImmutableFieldValidator(ABC):
    """Abstract validator for immutable/reserved field values."""

    RESERVED_VALUES: ClassVar[frozenset[str]] = frozenset()

    def __init__(
        self,
        matchers: Sequence[ImmutableFieldMatcher]
    ) -> None:
        self._reserved: tuple[str, ...] = tuple(type(self).RESERVED_VALUES)
        self._matchers: tuple[ImmutableFieldMatcher, ...] = tuple(matchers)

    def find_mimicked_value(
        self,
        candidate: str | None
    ) -> str | None:
        """
        Return the reserved value a candidate mimics, otherwise None.

        Strategies run cheapest/most precise first so the report names the
        tightest rule that fired.
        """
        if candidate is None:
            return None

        for matcher in self._matchers:
            matched: str | None = matcher.matches(
                candidate=candidate,
                reserved=self._reserved
            )

            if matched is not None:
                return matched

        return None

    @abstractmethod
    def validate_reserved_value(
        self,
        candidate: str | None
    ) -> None:
        """
        Reject a candidate that is empty or mimics a reserved value.

        Raises:
            HTTPException: When the candidate violates the API rules.
        """
