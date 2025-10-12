import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from alert.infrastructure.redis import redis

router = APIRouter()


ALERT_KEY = "latest_alert"
ALERT_CHANNEL = "alerts_channel"
ALERT_TTL_MINUTES = 30


Alert = dict[str, str | int | float]


class AlertInfo(BaseModel):
    data: Alert
    received_at: datetime


@router.post("/alerts")
@router.put("/alerts")
async def put_alert(alert: Alert):
    alert_data = {
        "data": alert,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    await redis.set(ALERT_KEY, json.dumps(alert_data), ex=ALERT_TTL_MINUTES * 60)

    await redis.publish(ALERT_CHANNEL, json.dumps(alert_data))

    return {"status": "alert stored", "alert": alert}


@router.get("/alerts")
async def get_alerts(request: Request):
    async def event_generator():
        pubsub = redis.pubsub()
        await pubsub.subscribe(ALERT_CHANNEL)

        last_alert_json = await redis.get(ALERT_KEY)
        if last_alert_json:
            alert_data = json.loads(last_alert_json)
            timestamp = datetime.fromisoformat(alert_data["timestamp"])
            if timestamp > datetime.now(tz=timezone.utc) - timedelta(
                minutes=ALERT_TTL_MINUTES
            ):
                alert_info = AlertInfo(
                    data=alert_data["data"], received_at=alert_data["timestamp"]
                )
                yield json.dumps(alert_info.model_dump(mode="json"))

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                # Stop if client disconnects
                if await request.is_disconnected():
                    break

                data = message["data"]
                data = json.loads(data)
                alert_info = AlertInfo(data=data["data"], received_at=data["timestamp"])
                yield json.dumps(alert_info.model_dump(mode="json")) + "\n"

        finally:
            await pubsub.unsubscribe(ALERT_CHANNEL)
            await pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
