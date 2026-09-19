import os
import sqlite3
import structlog

logger = structlog.get_logger()

# Enforce secure path naming conventions matching migrations parameters
DATABASE_PATH = "data/civic_gateway.db"

def initialize_database_vault():
    """Builds isolated relational storage directories and instantiates multi-tenant schemas."""
    # Ensure target data tracking folders exist on the laptop volume path
    if os.path.dirname(DATABASE_PATH):
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    logger.info("Initializing serverless database engine schema models...")
    
    # Hardening connection parameters with strict timeouts handles high concurrency traffic smoothly
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()
    
    try:
        # Activate WAL (Write-Ahead Logging) to allow concurrent asynchronous reading and writing loops
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        
        # Create the core multi-tenant report ledger table securely
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anonymous_ledger_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracker_token TEXT NOT NULL UNIQUE,
                tenant_id TEXT NOT NULL,
                matched_category TEXT NOT NULL,
                severity_level TEXT NOT NULL,
                regulatory_routing_target TEXT NOT NULL,
                anonymized_evidence_body TEXT NOT NULL,
                saved_media_path TEXT,
                keyword_match_density INTEGER DEFAULT 0,
                timestamp_utc DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Enforce high-speed indexes to prevent cross-tenant lookup delays
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenant ON anonymous_ledger_records(tenant_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_token ON anonymous_ledger_records(tracker_token)")
        
        conn.commit()
        logger.info("Serverless database tables and optimization indexes deployed successfully in WAL mode")
        
    except sqlite3.Error as e:
        logger.error("Catastrophic database initialization failure", error=str(e))
        raise e
    finally:
        conn.close()

def execute_storage_integrity_audit():
    """Runs a non-blocking diagnostic query pass to verify data tracking channels are open."""
    if not os.path.exists(DATABASE_PATH):
        logger.error("Storage audit aborted: Database file is missing from layout path parameters")
        return False
        
    conn = sqlite3.connect(DATABASE_PATH, timeout=5.0)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA journal_mode")
        current_mode = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM anonymous_ledger_records")
        logger.info("Database volume storage integrity check completed successfully [PASS]", journal_mode=current_mode)
        return True
    except sqlite3.Error as e:
        logger.error("Database storage integrity audit failed [FAIL]", error=str(e))
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    initialize_database_vault()
    execute_storage_integrity_audit()
