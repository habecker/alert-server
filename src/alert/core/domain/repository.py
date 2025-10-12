import logging
from pathlib import Path
from threading import Lock

from tinydb import Query, TinyDB

from alert.core.domain import (
    ApiKeySecret,
    ApiUser,
    Username,
    extract_username,
)
from alert.infrastructure.environment import environment

logger = logging.getLogger(__name__)

db = TinyDB(Path(environment.AUTH_STORE_DIR) / "auth.json")
db_lock = Lock()
users_table = db.table("users")


def _find_existing_user(
    username: Username,
) -> ApiUser | None:
    UserQ = Query()
    record = users_table.get(UserQ.username == username)
    return ApiUser(**record) if record else None


def create(username: Username) -> ApiKeySecret:
    user = _find_existing_user(username)
    if user:
        api_key = user.generate_api_key()
        with db_lock:
            users_table.update(
                user.model_dump(mode="json"), Query().username == username
            )
    else:
        user = ApiUser(username=username)
        api_key = user.generate_api_key()
        with db_lock:
            users_table.insert(user.model_dump(mode="json"))

    return api_key


def validate(api_key: ApiKeySecret) -> Username | None:
    username = extract_username(api_key)
    if not username:
        logger.warning("Received invalid api key with no user information")
        return None

    user = _find_existing_user(username)

    if not user:
        logger.warning(
            "Received invalid api key, the user %s does not exist",
            user,
        )
        return None

    if not user.validate_api_key(api_key):
        return None

    return user.username
