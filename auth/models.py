"""
Table Model imports required by the Auth BFF Framework.


SQLAlchemy configures every mapper in a registry together. This means a
``relationship()`` declared on one model makes the *other* model mandatory at
configure time even when this service never queries it. For example, ``Users``
declares ``role``, ``identities`` and ``chatboxes``, hence importing the model
alone makes the first query fail with::
    InvalidRequestError: When initializing mapper Mapper[Users(users)], expression
    'Chatboxes' failed to locate a name ('Chatboxes')

The framework only reads/writes ``users``, ``roles`` and ``user_identities``.
Therfore, we must not import ``Chatboxes`` for its own sake. It's only imported
here purely so the shared ``Users`` mapper can resolve, keeping the model
definitions themselves untouched (and compatible with the rest of Table Models).


TODO:
Once `COSMIC-379` ticket is implemented, the use of this file is no longer needed.
"""

### Core modules ###


### Type hints ###


### Internal modules ###
from app.apis.table_models.chatboxes import Chatboxes               # noqa: F401
from app.apis.table_models.roles import Roles                       # noqa: F401
from app.apis.table_models.user_identities import UserIdentities    # noqa: F401
from app.apis.table_models.users import Users                       # noqa: F401


__all__: list[str] = [
    "Chatboxes",
    "Roles",
    "UserIdentities",
    "Users"
]
