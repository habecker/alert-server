import redis.asyncio as redis

from alert.infrastructure.environment import environment

redis = redis.Redis(
    host=environment.REDIS_HOST,
    port=environment.REDIS_PORT,
    decode_responses=True,
)
