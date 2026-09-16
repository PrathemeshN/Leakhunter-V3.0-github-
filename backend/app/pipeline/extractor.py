import re
import spacy

# Load spaCy model (will fallback gracefully if not loaded)
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None

# Regex patterns
PATTERNS = {
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'),
    "pan_card": re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'),
    "aadhaar_card": re.compile(r'\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b'),
    "credit_card": re.compile(r'\b(?:\d[ -]*?){13,16}\b'), # Basic card number match
    "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "phone": re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
}


def extract_regex_pii(text: str) -> dict:
    """
    Runs regex matches for structured PII identifiers.
    """
    results = {}
    for key, regex in PATTERNS.items():
        matches = regex.findall(text)
        if matches:
            # Clean and deduplicate matches
            results[key] = list(set([m.strip() for m in matches]))
    return results


def extract_ner_pii(text: str) -> dict:
    """
    Runs spaCy NER to extract names, organizations, and geographical locations.
    """
    results = {
        "person": [],
        "organization": [],
        "gpe": [] # Geo-Political Entities (countries, cities, states)
    }
    
    if not nlp:
        return results
        
    try:
        # Avoid running on excessively large texts to save CPU
        doc = nlp(text[:50000]) 
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                results["person"].append(ent.text)
            elif ent.label_ == "ORG":
                results["organization"].append(ent.text)
            elif ent.label_ in ["GPE", "LOC"]:
                results["gpe"].append(ent.text)
                
        # Deduplicate
        for k in results:
            results[k] = list(set(results[k]))
    except Exception as e:
        # Silent fail or logger in production
        pass
        
    return results


def run_extraction_pipeline(text: str) -> dict:
    """
    Runs both regex and NER extractions and aggregates results.
    """
    regex_results = extract_regex_pii(text)
    ner_results = extract_ner_pii(text)
    
    # Merge findings
    all_pii = {**regex_results}
    
    # Map spaCy NER findings to our standard DataType naming
    if ner_results.get("person"):
        all_pii["person_names"] = ner_results["person"]
    if ner_results.get("organization"):
        all_pii["organizations"] = ner_results["organization"]
    if ner_results.get("gpe"):
        all_pii["affected_countries"] = ner_results["gpe"]
        
    return all_pii
