"""
Client for the IAM management API exposed by `cosmic-auth`.

The Auth BFF is the only service allowed to talk to the IAM. The database
endpoints therefore push a mutation here first and only write the local row once
the IAM accepted it.
"""


### Core modules ###
from fastapi import (
    HTTPException,
    status
)
from httpx import (
    AsyncClient,
    HTTPError
)
from http import HTTPStatus
from urllib.parse import quote


### Type hints ###
from typing import Any


### Internal modules ###
from ..cores.configs import COSMIC_AUTH_URL


_AUTH_IAM_USERS_PATH: str = "/api/v1/users"
_AUTH_IAM_ROLES_PATH: str = "/api/v1/roles"
_AUTH_REQUEST_TIMEOUT: float = 15.0


def _status_label(status_code: int) -> str:
    try:
        return f"{status_code} - {HTTPStatus(status_code).phrase}"

    except ValueError:
        return str(status_code)


def _error_detail(response: Any) -> dict[str, Any]:
    try:
        payload: Any = response.json()

    except ValueError:
        payload = None

    detail: Any = (
        payload.get(
            "detail",
            payload
        )
        if   (isinstance(payload, dict))
        else (payload)
    )

    if isinstance(detail, dict):
        return detail

    return {
        "status": _status_label(response.status_code),
        "message": (
            str(detail)
            if   (detail)
            else ("The auth micro-service rejected the IAM request.")
        )
    }


async def _request(
    method:     str,
    path:       str,
    payload:    dict[str, Any] | None = None
) -> Any:
    request_kwargs: dict[str, Any] = {}

    if payload is not None:
        request_kwargs["json"] = payload

    try:
        async with AsyncClient(
            base_url=str(COSMIC_AUTH_URL).rstrip("/"),
            timeout=_AUTH_REQUEST_TIMEOUT
        ) as client:
            response = await client.request(
                method=method,
                url=path,
                **request_kwargs
            )

    except HTTPError as auth_exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "status": "502 - Bad Gateway",
                "message": f"The auth micro-service is unreachable: {auth_exc}"
            }
        )

    if response.is_error:
        raise HTTPException(
            status_code=response.status_code,
            detail=_error_detail(response=response)
        )

    if not response.content:
        return {}

    try:
        return response.json()

    except ValueError:
        return {}


async def update_iam_user(
    user_id:    str,
    payload:    dict[str, Any]
) -> dict[str, Any]:
    return await _request(
        method="PATCH",
        path=f"{_AUTH_IAM_USERS_PATH}/{quote(string=user_id, safe='')}",
        payload=payload
    )


async def delete_iam_user(
    user_id: str
) -> dict[str, Any]:
    return await _request(
        method="DELETE",
        path=f"{_AUTH_IAM_USERS_PATH}/{quote(string=user_id, safe='')}"
    )


async def create_iam_role(
    name:   str,
    desc:   str | None
) -> dict[str, Any]:
    return await _request(
        method="POST",
        path=_AUTH_IAM_ROLES_PATH,
        payload={
            "name": name,
            "desc": desc
        }
    )


async def update_iam_role(
    name:       str,
    payload:    dict[str, Any]
) -> dict[str, Any]:
    return await _request(
        method="PATCH",
        path=f"{_AUTH_IAM_ROLES_PATH}/{quote(string=name, safe='')}",
        payload=payload
    )


async def delete_iam_role(
    name: str
) -> dict[str, Any]:
    return await _request(
        method="DELETE",
        path=f"{_AUTH_IAM_ROLES_PATH}/{quote(string=name, safe='')}"
    )
