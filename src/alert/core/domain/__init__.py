import base64
import datetime
import hashlib
import os
import secrets
import uuid

import pydantic

ApiKeySecret = str
Username = str
Password = bytes


def generate_api_key(user: Username, num_bytes: int = 24) -> ApiKeySecret:
    random_bytes = secrets.token_bytes(num_bytes)
    random_bytes = user.encode("utf-8") + b":" + random_bytes

    api_key = base64.urlsafe_b64encode(random_bytes).decode("utf-8")
    return api_key.rstrip("=")


def extract_username(api_key: ApiKeySecret) -> Username | None:
    padding = "=" * (4 - (len(api_key) % 4))
    padded_key = api_key + padding

    try:
        decoded_bytes = base64.urlsafe_b64decode(padded_key)
    except base64.binascii.Error:
        return None  # Invalid base64 string

    try:
        username_bytes, _ = decoded_bytes.split(b":", 1)
        return username_bytes.decode("utf-8")
    except ValueError:
        return None


class ApiKey(pydantic.BaseModel):
    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    created_at: datetime.datetime = pydantic.Field(
        default_factory=datetime.datetime.now
    )
    salt: str | None = pydantic.Field(default=None)
    hash: str | None = pydantic.Field(default=None)

    def _hash(self, password: ApiKeySecret) -> str:
        assert self.salt is not None, "Cannot hash api key without salt"
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            self.salt.encode(),
            100000,
        ).hex()

    def initialize(self, username: str) -> ApiKeySecret:
        password = generate_api_key(username)
        self.salt = os.urandom(16).hex()
        self.hash = self._hash(password)
        return password

    def validate_api_key(self, api_key: ApiKeySecret) -> bool:
        return self.hash == self._hash(api_key)


class ApiUser(pydantic.BaseModel):
    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    created_at: datetime.datetime = pydantic.Field(
        default_factory=datetime.datetime.now
    )

    username: Username

    api_keys: list[ApiKey] = list()

    def generate_api_key(self) -> ApiKeySecret:
        api_key = ApiKey()
        secret = api_key.initialize(self.username)
        self.api_keys.append(api_key)
        return secret

    def validate_api_key(self, api_key: ApiKeySecret) -> bool:
        for api_key_entity in self.api_keys:
            if api_key_entity.validate_api_key(api_key):
                return True
        return False
