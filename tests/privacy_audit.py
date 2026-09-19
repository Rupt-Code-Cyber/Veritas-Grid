import pytest
from core.identity_scrubber import CivicIdentityScrubber

@pytest.fixture
def scrubber():
    return CivicIdentityScrubber(secret_salt="test_cryptographic_verification_salt_hash_matrix_string_64")

def test_aggressive_pii_erasure_scenarios(scrubber):
    """Audits the regular expression engine against complex, nested identification strings."""
    # Test case: Complete identification blocks wrapped in common whistleblower vernacular
    raw_payload_a = "My name is Chidi, my email is admin@mainbank.com.ng and you can reach me at +2348031234567."
    scrubbed_a = scrubber.scrub_report_text(raw_payload_a)
    
    assert "[NAME_INTRO_REDACTED]" in scrubbed_a
    assert "[EMAIL_REDACTED]" in scrubbed_a
    assert "[PHONE_REDACTED]" in scrubbed_a
    assert "Chidi" not in scrubbed_a
    assert "admin@mainbank.com.ng" not in scrubbed_a
    assert "+2348031234567" not in scrubbed_a

    # Test case: Subtle inline fragments trapped without clipping surrounding vocabulary
    raw_payload_b = "Please contact me at chidi.egwu@gov.ng or dial 08029876543 immediately."
    scrubbed_b = scrubber.scrub_report_text(raw_payload_b)
    
    assert "[EMAIL_REDACTED]" in scrubbed_b
    assert "[PHONE_REDACTED]" in scrubbed_b
    assert "Please contact me at" in scrubbed_b

def test_tracker_token_irreversibility(scrubber):
    """Ensures anonymous receipt tracking tokens are consistently generated as static 64-char hashes."""
    seed_input = "+2348031234567"
    token_a = scrubber.generate_anonymous_tracker(seed_input)
    token_b = scrubber.generate_anonymous_tracker(seed_input)
    
    assert len(token_a) == 64
    assert token_a == token_b  # Deterministic tracking capability
    assert seed_input not in token_a  # Total cryptographic masking
