from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from crie.search_api import router as search_router
from crie.workload.schemas import (  # Existing workload schemas if available
    WorkloadCalculationRequest,
    WorkloadCalculationResponse,
)

app = FastAPI(
    title="CRIE Assistant API",
    description="Digital knowledge base and AI assistant service for Central Research Institute of Epidemiology",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "crie-assistant-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("crie_assistant_api:app", host="0.0.0.0", port=8000, reload=True)
