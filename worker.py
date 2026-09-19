import os
import sqlite3
from typing import Optional
import taskiq
import structlog

logger = structlog.get_logger()

# 1. Immediate Testing Short-Circuit prevents Python 3.13 environment import crashes entirely
if os.getenv("ENVIRONMENT") == "testing":
    broker = taskiq.InMemoryBroker()
else:
    # Production-ready compiled Redis paths are evaluated purely under live cluster runtimes
    from taskiq_redis import RedisAsyncBroker
    broker = RedisAsyncBroker("redis://redis_broker:6379/0")

# 2. Instantiate persistent logic routing utilities globally to maximize cache reuse across tasks
from core.rag_classifier import CivicReportClassifier
from core.media_processor import CivicMediaProcessor

classifier = CivicReportClassifier()
media_processor = CivicMediaProcessor()
DATABASE_PATH = "data/civic_gateway.db"

@broker.task
async def process_intake_task_pipeline(
    raw_text: str,
    tracker_token: str,
    tenant_id: str,
    tier_context: str,
    has_media: bool = False,
    media_binary: Optional[bytes] = None,
    file_name: Optional[str] = None
) -> bool:
    """Background worker execution node processing taxonomy matrices asynchronously."""
    logger.info("Asynchronous task consumer picking up report payload tracking sequence")
    
    classification = classifier.classify_text(raw_text)
    matched_category = classification["matched_category"]
    severity_level = classification["severity_level"]
    routing_target = classification["regulatory_routing_target"]
    match_density = classification["keyword_match_density"]
    
    saved_media_path = None
    
    if has_media and media_binary and file_name:
        media_result = media_processor.process_and_isolate_media(
            raw_binary_data=media_binary,
            file_name=file_name,
            tenant_id=tenant_id,
            current_tier=tier_context
        )
        if media_result["status"] == "VERIFIED_EXIF_PURGED_AND_STORED":
            saved_media_path = media_result["saved_path"]

    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("""
            INSERT INTO anonymous_ledger_records (
                tracker_token, tenant_id, matched_category, severity_level, 
                regulatory_routing_target, anonymized_evidence_body, 
                saved_media_path, keyword_match_density
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tracker_token, tenant_id, matched_category, severity_level,
            routing_target, raw_text, saved_media_path, match_density
        ))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error("Database persistence pipeline execution failure", error=str(e))
        return False
    finally:
        conn.close()
