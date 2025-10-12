from fastapi import Depends, FastAPI, HTTPException, Request, Response, Security, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from alert.core.adapter import verify_token
from alert.infrastructure.environment import environment

security = HTTPBearer(auto_error=False)

if environment.stage == "prod":
    app = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        dependencies=[
            Security(security),
        ],
    )
else:
    app = FastAPI(
        dependencies=[
            Security(security),
        ],
    )


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Skip specific public endpoints
    if environment.stage != "prod":
        if request.url.path in ["/docs", "/openapi.json"]:
            return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    token = auth_header.split(" ", 1)[1]

    user_info = verify_token(token)

    if not user_info:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    request.state.user_info = user_info

    return await call_next(request)


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse, include_in_schema=True)
def health_check():
    return HealthResponse(status="ok")


def main():
    import uvicorn

    uvicorn.run(
        "alert.app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        headers=[("Cache-Control", "no-cache")],
    )


if __name__ == "__main__":
    main()
