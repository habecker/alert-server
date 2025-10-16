import json
from datetime import datetime, timedelta, timezone

from click import group
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
@router.post("/alerts/{group_name}")
@router.put("/alerts/{group_name}")
async def put_alert(
    alert: Alert,
    group_name: str = "default",
):
    alert_data = {
        "data": alert,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    await redis.set(
        ALERT_KEY + "-" + group_name, json.dumps(alert_data), ex=ALERT_TTL_MINUTES * 60
    )

    await redis.publish(ALERT_CHANNEL + "-" + group_name, json.dumps(alert_data))

    return {"status": "alert stored", "alert": alert}


@router.get("/alerts")
@router.get("/alerts/{group_name}")
async def get_alerts(request: Request, group_name="default"):
    async def event_generator():
        HEARTBEAT_INTERVAL_SECONDS = 15
        pubsub = redis.pubsub()
        channel = ALERT_CHANNEL + "-" + group_name
        await pubsub.subscribe(channel)

        last_alert_json = await redis.get(ALERT_KEY + "-" + group_name)
        if last_alert_json:
            alert_data = json.loads(last_alert_json)
            timestamp = datetime.fromisoformat(alert_data["timestamp"])
            if timestamp > datetime.now(tz=timezone.utc) - timedelta(
                minutes=ALERT_TTL_MINUTES
            ):
                alert_info = AlertInfo(
                    data=alert_data["data"], received_at=alert_data["timestamp"]
                )
                payload = json.dumps(alert_info.model_dump(mode="json"))
                # SSE frame with data line and terminating blank line
                yield f"data: {payload}\n\n"

        try:
            # Poll for messages with timeout to allow heartbeat
            while True:
                # Stop if client disconnects
                if await request.is_disconnected():
                    break

                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=HEARTBEAT_INTERVAL_SECONDS
                )

                if message is None:
                    # Heartbeat comment to keep connection alive (ignored by clients)
                    yield ": keep-alive\n\n"
                    continue

                if message.get("type") != "message":
                    continue

                data = message["data"]
                data = json.loads(data)
                alert_info = AlertInfo(data=data["data"], received_at=data["timestamp"])
                payload = json.dumps(alert_info.model_dump(mode="json"))
                yield f"data: {payload}\n\n"

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    # Add standard SSE headers to prevent buffering and caching
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        event_generator(), media_type="text/event-stream", headers=headers
    )
