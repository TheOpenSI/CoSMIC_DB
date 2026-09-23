### Core modules ###
from datetime import datetime
from uuid import (
    UUID,
    SafeUUID
)


### Type hints ###
from typing import Any


### Internal modules ###


IMMUTABLE_FIELDS: tuple[str, ...] = (
    "inquiry_cycle_id",
    "user_role",
    "query_create_on",
    "llm_role",
    "response_create_on",
    "input_token",
    "output_token"
)


def _valid_uuidv7(obj: Any) -> bool:
    if isinstance(obj, UUID):
        # For our case, it must be in UUIDv7 format. Default UUID type is in
        # UUIDv4 format
        return False

    if isinstance(obj, str):
        try:
            UUID(
                hex=str(obj),
                version=7,
                is_safe=SafeUUID.safe
            )
            return True

        except ValueError:
            return False

    return False


def _valid_timestamp(obj: Any) -> bool:
    if isinstance(obj, datetime):
        return True

    if isinstance(obj, str):
        try:
            datetime.fromisoformat(obj)
            return True

        except ValueError:
            return False

    return False


def validate_immutable_field(
    current_data:   list[dict[str, Any]],
    incoming_data:  list[dict[str, Any]]
) -> bool:
    """
    Validates incoming chat history based on size matching.

    Per our business logic, the matching logic would be handled accordingly:

    1. Equal size
        Validates immutable fields across all records.

    2. Larger size
        Skips the matching overlap and validates only the data types of
        extra records.

    3. Smaller size
        This would never happens unless getting API injection attacks

    Args:
        current_data:
            stored chat history data.

        incoming_data:
            requested chat history data.

    Returns:
        True if chat history data doesn't contains immutable fields (with/without
        invalid value format). If it does, returns False.

    Example:
        >>> is_validate: bool = validate_immutable_field(
        >>>     current_data=chat_history_current_data,
        >>>     incoming_data=chat_history_incoming_data
        >>> )
        >>> print(is_validate)
        >>> True
    """
    current_len:  int = len(current_data)
    incoming_len: int = len(incoming_data)

    # Case 1: Same size -> check immutable fields across all matching indices
    if current_len == incoming_len:
        for i in range(current_len):
            current_block_data:     dict[str, Any] = current_data[i]
            incoming_block_data:    dict[str, Any] = incoming_data[i]

            for immutable_field in IMMUTABLE_FIELDS:
                if (
                    immutable_field in current_block_data
                    or
                    immutable_field in incoming_block_data
                ):
                    if current_block_data.get(immutable_field) != incoming_block_data.get(immutable_field):
                        return False

    # Case 2: Larger size -> skip overlap check, only type-check extra records
    elif incoming_len > current_len:
        extra_datas: list[dict[str, Any]] = incoming_data[current_len:]

        for extra_data in extra_datas:
            if (
                "inquiry_cycle_id" in extra_data
                and
                not _valid_uuidv7(obj=extra_data["inquiry_cycle_id"])
            ):
                return False

            if any(
                timestamp_field in extra_data
                and not _valid_timestamp(obj=extra_data[timestamp_field])
                for timestamp_field in (
                    "query_create_on",
                    "response_create_on"
                )
            ):
                return False

    # Case 3: Smaller size -> unexpected state
    else:
        return False

    return True
