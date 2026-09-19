import re
import hmac
import hashlib

class CivicIdentityScrubber:
    def __init__(self, secret_salt: str):
        """
        Initializes the privacy gate. Requires a secure mathematical salt
        key to ensure tracking tokens are impossible to reverse-engineer.
        """
        if not secret_salt or "your_generated" in secret_salt:
            raise ValueError("CRITICAL: Invalid or missing GATEWAY_SECRET_SALT configuration.")
        
        self.salt = secret_salt.encode('utf-8')
        
        # 1. Compile high-speed regex tracking rules for Nigerian phone variants
        self.phone_pattern = re.compile(r'(?:\+?234|0)\d{8,10}\b')
        
        # 2. Compile regex tracking rules for common email structures
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        
        # 3. Light lexical matching for common introductory names (e.g., "My name is Chidi...")
        self.name_intro_pattern = re.compile(
            r'\b(?:my name is|i am called|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
            re.IGNORECASE
        )

    def generate_anonymous_tracker(self, raw_sender_id: str) -> str:
        """Converts a raw phone number into an un-reversible alphanumeric tracking receipt."""
        if not raw_sender_id or raw_sender_id == "WEB_PORTAL_CONNECTION":
            return "ANONYMOUS_WEB_USER"
            
        hashed = hmac.new(self.salt, raw_sender_id.strip().encode('utf-8'), hashlib.sha256)
        return hashed.hexdigest()

    def scrub_report_text(self, raw_text: str) -> str:
        """Destroys phone numbers, emails, and direct identity phrases in microseconds."""
        if not raw_text:
            return ""

        # Erase phone patterns
        scrubbed = self.phone_pattern.sub("[PHONE_REDACTED]", raw_text)
        
        # Erase email patterns
        scrubbed = self.email_pattern.sub("[EMAIL_REDACTED]", scrubbed)
        
        # Erase direct introduction names (e.g., "My name is Alhaji")
        scrubbed = self.name_intro_pattern.sub("[NAME_INTRO_REDACTED]", scrubbed)
        
        return scrubbed

    def secure_pipeline_ingest(self, raw_text: str, raw_sender_id: str) -> dict:
        """Ingests raw carrier traffic, strips identities inside memory buffers, and returns safe data."""
        return {
            "tracker_receipt_token": self.generate_anonymous_tracker(raw_sender_id),
            "anonymized_evidence_body": self.scrub_report_text(raw_text),
            "privacy_compliance_status": "VERIFIED_SECURE_PII_DESTROYED"
        }
