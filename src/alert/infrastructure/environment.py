import os
from enum import StrEnum
from typing import Any, TypeVar


class EnvironmentKeys(StrEnum):
    AUTH_STORE_DIR = "AUTH_STORE_DIR"
    STAGE = "STAGE"
    REDIS_HOST = "REDIS_HOST"
    REDIS_PORT = "REDIS_PORT"


_REQUIRED_ENVIRONMENT_KEYS = []


class _Environment:
    @staticmethod
    def validate() -> None:
        missing_keys = [
            key for key in _REQUIRED_ENVIRONMENT_KEYS if not _Environment._has_key(key)
        ]
        if missing_keys:
            msg = f"Missing environment variables: {', '.join(missing_keys)}"
            raise ValueError(msg)

    @staticmethod
    def _has_key(key: str) -> bool:
        return key in os.environ

    T = TypeVar("T")

    @staticmethod
    def _get_env(key: str) -> T:
        key = key.upper()
        if key in os.environ:
            return os.environ[key]
        msg = f"Environment variable {key} is not set"
        raise KeyError(msg)

    def get_or_default(self, key: str, default: T) -> T:
        key = key.upper()
        return os.environ.get(key, default)

    def __getattribute__(self, name: str, /) -> Any:
        if name in {"get_or_default"}:
            return super().__getattribute__(name)

        return _Environment._get_env(name)


Environment = _Environment


environment = _Environment()
_Environment.validate()
