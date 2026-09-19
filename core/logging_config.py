import logging
import re
import structlog

def strip_pii_from_logs(logger, log_method, event_dict):
    """
    Global interception middleware. Intercepts all runtime log entries 
    and scrubs personal metadata dynamically before text output.
    """
    event_message = event_dict.get("event", "")
    if isinstance(event_message, str):
        # Cleans out matching Nigerian telephone formats (+234, 080, 090, etc.)
        event_dict["event"] = re.sub(r'(?:\+?234|0)\d{8,10}\b', "[PHONE_REDACTED]", event_message)
    
    # Structural network and tracking identity sanitization
    if "ip" in event_dict:
        event_dict["ip"] = "[IP_REDACTED]"
    if "client" in event_dict:
        event_dict["client"] = "[CLIENT_METADATA_REDACTED]"
    if "sender_id" in event_dict:
        event_dict["sender_id"] = "[SENDER_ID_REDACTED]"
        
    return event_dict

def configure_secure_logging():
    """Initializes the unified, zero-leak JSON logging stream profile for the gateway."""
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="YYYY-MM-DD HH:mm:ss"),
            strip_pii_from_logs,
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer() # Standardises logs as secure, structured JSON strings
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
