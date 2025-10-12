from dataclasses import dataclass

from alert.core.domain import ApiKeySecret, Username, repository


@dataclass
class UserInfo:
    username: Username


def create(username: Username) -> ApiKeySecret:
    return repository.create(username)


def validate(api_key: ApiKeySecret) -> UserInfo | None:
    username = repository.validate(api_key)
    return UserInfo(username) if username else None
