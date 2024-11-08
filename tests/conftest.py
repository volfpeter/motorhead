# -- Fixture registration
from .fixtures.database_fixture import (
    database,  # noqa: F401
    db_client,  # noqa: F401
    db_connect_string,  # noqa: F401
    sync_db_client,  # noqa: F401
)
from .fixtures.event_loop_fixture import event_loop  # noqa: F401
