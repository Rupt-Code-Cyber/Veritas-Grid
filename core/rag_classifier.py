import json
import re
import structlog

logger = structlog.get_logger()

class CivicReportClassifier:
    def __init__(self, taxonomy_path: str = "config/taxonomy.json"):
        """Loads and compiles lookaround regular expression matrices from hot-swappable JSON files."""
        self.taxonomy_path = taxonomy_path
        try:
            with open(self.taxonomy_path, "r") as f:
                self.taxonomy = json.load(f)
            logger.info("Taxonomy mapping metrics loaded successfully into processing cache")
        except Exception as e:
            logger.error("Failed to parse taxonomy configuration mapping, applying baseline fallback rules", error=str(e))
            self.taxonomy = {
                "categories": [],
                "baseline_default_category": "General Corporate Abuse",
                "baseline_default_severity": "LOW",
                "baseline_default_routing_target": "Ministry of Labour Exploitation Unit"
            }

    def classify_text(self, plain_text: str) -> dict:
        """Calculates keyword match density using multi-word boundary lookarounds."""
        cleaned_input = plain_text.lower()
        
        # Pull system baselines natively from the config mapping layout parameters
        matched_category = self.taxonomy.get("baseline_default_category", "General Corporate Abuse")
        severity_level = self.taxonomy.get("baseline_default_severity", "LOW")
        routing_target = self.taxonomy.get("baseline_default_routing_target", "Ministry of Labour Exploitation Unit")
        max_density = 0

        # Meticulously loop through the category collection array block
        categories = self.taxonomy.get("categories", [])
        for cat in categories:
            current_density = 0
            patterns = cat.get("lookaround_match_patterns", [])
            
            for pattern in patterns:
                # Bound tokens tightly using word-boundary regular expressions to prevent mid-word clips
                regex_rule = rf"\b{re.escape(pattern.lower())}\b"
                matches = re.findall(regex_rule, cleaned_input)
                current_density += len(matches)

            # Optimistic scoring override traps the category with the highest density metrics footprint
            if current_density > max_density:
                max_density = current_density
                matched_category = cat.get("name")
                severity_level = cat.get("severity")
                routing_target = cat.get("target_routing_agency")

        return {
            "matched_category": matched_category,
            "severity_level": severity_level,
            "regulatory_routing_target": routing_target,
            "keyword_match_density": max_density
        }
