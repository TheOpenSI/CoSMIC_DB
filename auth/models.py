"""Table-model imports required by the Auth BFF.

SQLAlchemy configures every mapper in a registry together: a ``relationship()``
declared on one model makes the *other* model mandatory at configure time even
when this service never queries it. ``Users`` declares ``role``, ``identities``
and ``chatboxes``, so importing ``Users`` alone makes the first query fail with::

    InvalidRequestError: When initializing mapper Mapper[Users(users)],
    expression 'Chatboxes' failed to locate a name ('Chatboxes')

The Auth BFF only reads/writes ``users``, ``roles`` and ``user_identities``, so
it does not import ``Chatboxes`` for its own sake — it is imported here purely
so the shared ``Users`` mapper can resolve, keeping the model definitions
themselves untouched (and compatible with the main `cosmic-db` backend).
"""

### Core modules ###


### Type hints ###


### Internal modules ###
from app.apis.table_models.chatboxes import Chatboxes  # noqa: F401
from app.apis.table_models.roles import Roles  # noqa: F401
from app.apis.table_models.user_identities import UserIdentities  # noqa: F401
from app.apis.table_models.users import Users  # noqa: F401


__all__: list[str] = [
    "Chatboxes",
    "Roles",
    "UserIdentities",
    "Users"
]
