from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import time
from telemetry_collector import global_telemetry

app = FastAPI(title="CRIE Assistant API", version="1.0.0")

class SearchPingRequest(BaseModel):
    latency_ms: float = Field(..., ge=0.0, description="Search roundtrip or execution latency in ms")
    result_count: int = Field(..., ge=0, description="Count of matched results")
    query_length: Optional[int] = Field(default=0, ge=0, description="Length of query characters for metric aggregation")

class ClickPingRequest(BaseModel):
    rank: int = Field(..., ge=0, description="Rank position clicked by user")
    doc_token: Optional[str] = Field(default=None, description="Anonymized doc reference token")

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": time.time()}

@app.post("/api/v1/telemetry/search-ping", status_code=status.HTTP_202_ACCEPTED)
def record_search_ping(payload: SearchPingRequest):
    """
    Accepts anonymous search metrics and updates in-memory GQM collector in <5ms without storing PII.
    """
    global_telemetry.record_search(
        latency_ms=payload.latency_ms,
        result_count=payload.result_count,
        query_length=payload.query_length
    )
    return {"status": "recorded"}

@app.post("/api/v1/telemetry/click-ping", status_code=status.HTTP_202_ACCEPTED)
def record_click_ping(payload: ClickPingRequest):
    """
    Accepts anonymous click rank metrics for search evaluation.
    """
    global_telemetry.record_click(
        rank=payload.rank,
        document_id=payload.doc_token
    )
    return {"status": "recorded"}

@app.get("/api/v1/telemetry/metrics")
def get_telemetry_metrics() -> Dict[str, Any]:
    """
    Returns aggregated GQM search telemetry: average latency, zero-result counts, average click-through rank.
    """
    return global_telemetry.get_summary()
