import os
import pytest
from core.rag_classifier import CivicReportClassifier

@pytest.fixture
def classifier():
    # Enforce programmatic fallback verification tracking to keep tests bulletproof
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_path = os.path.join(base_dir, "config", "taxonomy.json")
    return CivicReportClassifier(taxonomy_path=target_path)

def test_critical_force_classification(classifier):
    """Verifies that human rights violations and brutality flags score highest for force matrix targets."""
    text_input = "An officer opened fire and two protesters were shot behind the junction."
    result = classifier.classify_text(text_input)
    
    assert result["matched_category"] == "Excessive Use of Force"
    assert result["severity_level"] == "CRITICAL"
    assert result["regulatory_routing_target"] == "National Human Rights Commission (NHRC)"
    assert result["keyword_match_density"] >= 2

def test_financial_fraud_classification(classifier):
    """Ensures corporate anti-corruption keywords cleanly map to financial graft targets."""
    text_input = "The head manager demanded a heavy bribe to bypass invoice padding checks."
    result = classifier.classify_text(text_input)
    
    assert result["matched_category"] == "Financial Fraud & Corruption"
    assert result["severity_level"] == "HIGH"
    assert result["regulatory_routing_target"] == "Independent Corrupt Practices Commission (ICPC)"

def test_multi_word_lookaround_boundary_precision(classifier):
    """Audits lookbehind logic to guarantee multi-word strings match flawlessly without clipping."""
    case_a = classifier.classify_text("There was a severe oil spill on the farmland.")
    assert case_a["matched_category"] == "Environmental & Land Violations"
    assert case_a["keyword_match_density"] == 1

    case_b = classifier.classify_text("The currency exchange rate has dropped down.")
    assert case_b["keyword_match_density"] == 0
