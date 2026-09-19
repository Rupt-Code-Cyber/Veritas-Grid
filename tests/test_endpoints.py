import pytest

def test_health_check_endpoint_metrics(test_client):
    """Validates the system health path node for cluster container environment telemetry tracking."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["ingestion_engine"] == "ACTIVE"

def test_anonymous_web_submission_parsing(test_client):
    """Verifies form-urlencoded text submissions parse seamlessly and trigger processing queues."""
    payload = {"report_body": " Whistleblower evidence text block containing corruption tracking flags. "}
    response = test_client.post("/v1/webhooks/web", data=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACCEPTED_FOR_ASYNC_PROCESSING"
    assert "tracker_receipt_token" in data
    assert len(data["tracker_receipt_token"]) == 64

def test_web_submission_empty_payload_rejection(test_client):
    """Guarantees the perimeter gateway throws clear 400 anomalies on missing submission parameters."""
    response = test_client.post("/v1/webhooks/web", data={"report_body": "   "})
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]

def test_twilio_whatsapp_chatbot_menu_progression(test_client):
    """Audits conversational state routing sequences inside the Redis session cache framework."""
    # Step 1: Fire an initial inbound text packet from a fresh phone line to trigger the organization selection card
    payload_step1 = {
        "MessageSid": "SM00000000000000000000000000000000",
        "From": "whatsapp:+2348039999999",
        "To": "whatsapp:+2348030000000",
        "Body": "Hello"
    }
    response_step1 = test_client.post("/v1/webhooks/whatsapp", data=payload_step1)
    assert response_step1.status_code == 200
    assert "text/xml" in response_step1.headers["content-type"]
    assert "Please select your target routing target agency number" in response_step1.text

    # Step 2: Pass a valid numerical choice string to pin down the multi-tenant organization routing target
    payload_step2 = payload_step1.copy()
    payload_step2["Body"] = "4"  # Select ICPC Anti-Corruption Bureau
    response_step2 = test_client.post("/v1/webhooks/whatsapp", data=payload_step2)
    assert "Target Organization Locked" in response_step2.text

    # Step 3: Stream the core text report information to complete the background transaction loop
    payload_step3 = payload_step1.copy()
    payload_step3["Body"] = "The director demanded a massive kickback bribe payment to clear the clearing layout block."
    response_step3 = test_client.post("/v1/webhooks/whatsapp", data=payload_step3)
    assert "Secure Submission Captured Successfully" in response_step3.text
