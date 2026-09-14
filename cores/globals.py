### Core modules ###
from datetime import (
    datetime,
    timezone
)


### Type hints ###
from typing import Any


### Internal modules ###



USER_ROLE:      str             = 'user'
LLM_ROLE:       str             = 'assistant'
SYSTEM_ROLES:   tuple[str, str] = ("admin", "user")


OPENAPI_GET_EXTRA_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "Requested Data Not Found",
        "content": {
            "application/json": {
                "example": {
                    "detail": {
                        "status": "404 - Not Found",
                        "message": "string"
                    }
                }
            }
        }
    }
}

OPENAPI_POST_EXTRA_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "description": "Invalid Payload Received",
        "content": {
            "application/json": {
                "example": {
                    "detail": {
                        "status": "400 - Bad Request",
                        "message": "string"
                    }
                }
            }
        }
    },
    409: {
        "description": "Foreign Key Integrity Constraint Error / Matching Data Found",
        "content": {
            "application/json": {
                "example": {
                    "detail": {
                        "status": "409 - Conflict",
                        "message": "string"
                    }
                }
            }
        }
    }
}

OPENAPI_PATCH_EXTRA_RESPONSES: dict[int | str, dict[str, Any]] = {
    **OPENAPI_GET_EXTRA_RESPONSES,
    **OPENAPI_POST_EXTRA_RESPONSES
}

OPENAPI_DELETE_EXTRA_RESPONSES: dict[int | str, dict[str, Any]] = {
    **OPENAPI_GET_EXTRA_RESPONSES
}


MONTH_LABELS: list[str] = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    """Return (year, month) with month in 1-12 after applying offset."""
    index = (year * 12 + (month - 1)) + offset
    return index // 12, (index % 12) + 1


def get_rolling_year_months(months: int) -> list[tuple[int, int]]:
    now = datetime.now(tz=timezone.utc)
    current_year = now.year
    current_month = now.month

    return [
        shift_month(current_year, current_month, offset - (months - 1))
        for offset in range(months)
    ]
