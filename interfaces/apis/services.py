### Core modules ###
from fastapi import (
    HTTPException,
    status
)


### Type hints ###
from typing import (
    ClassVar,
    Final,
    override
)
from pydantic.types import PositiveInt


### Internal modules ###
from ..abstracts.validators import ImmutableFieldValidator
from ...libraries.l337.matcher import (
    ImmutableFieldExactMatcher,
    ImmutableFieldFillerStripMatcher,
    ImmutableFieldFuzzyMatcher,
    ImmutableFieldLeetRegexMatcher
)
from ...cores.db import SessionDependency
from ...apis.table_models.services import Services


# Filler words an attacker may inject around/inside a core service name to
# disguise it (e.g., 'service_chess', 'ch_service_ess', 'core-memory')
CORE_SERVICES_NOISES: tuple[str, ...] = (
    "service",
    "services",
    "core",
    "core_service",
    "default",
    "system",
    "srv",
    "svc",
    "official"
)


class ServiceImmutableFieldValidator(ImmutableFieldValidator):
    """Enforce immutability of the default core services."""

    RESERVED_VALUES: ClassVar[frozenset[str]] = frozenset(
        {
            "chess",
            "memory",
            "code_generation",
            "general_question_answering",
            "academic_governance"
        }
    )

    def __init__(
        self,
        session: SessionDependency
    ) -> None:
        super().__init__(
            matchers=(
                ImmutableFieldExactMatcher(),
                ImmutableFieldLeetRegexMatcher(),
                ImmutableFieldFillerStripMatcher(noises=CORE_SERVICES_NOISES),
                ImmutableFieldFuzzyMatcher()
            )
        )
        self._session: Final[SessionDependency] = session

    @override
    def validate_reserved_value(
        self,
        candidate: str | None
    ) -> None:
        if (
            candidate is None
            or
            not candidate.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "400 - Bad Request",
                    "message": "Service name cannot be empty."
                }
            )

        if self.find_mimicked_value(candidate) is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                # NOTE:
                # just being a little humour here instead of the lame 400
                # error message since this's definitely an attack
                detail={
                    "status": "400 - Bad Request",
                    "message": "This is way too classic. Can you try something harder?"
                }
            )

        return None

    def validate_immutable_target(
        self,
        service_id: PositiveInt
    ) -> Services:
        """
        Resolve the service being updated and enforce core service immutability.

        A default core service is immutable, so any update request targeting
        one is rejected regardless of which fields the payload carries.

        Raises:
            HTTPException:
                404 when missing, 403 when the target is a core service.
        """
        service_db: Services | None = self._session.get(
            entity=Services,
            ident=service_id
        )

        if service_db is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service Not Found!"
            )

        if service_db.name.lower() in self.RESERVED_VALUES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "403 - Forbidden",
                    "message": f"Default core service [{service_db.name}] cannot be modified."
                }
            )

        return service_db
