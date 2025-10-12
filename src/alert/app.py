from fastapi import Depends, FastAPI
from pydantic import BaseModel

from alert.core.adapter import verify_token

app = FastAPI(dependencies=[Depends(verify_token)])


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
