import os
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
import logging

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "leak_classifier.joblib")

# Default training seed data for LeakHunter V2 out-of-the-box model initialization
SEED_TEXTS = [
    # Credentials / Hashes
    "admin:password123, root:secretpass, testuser:pass1",
    "john.doe@gmail.com:$2b$12$eFzRwh8j10Zc/aXbNfDfgO",
    "database dump user credentials password email md5 hash sha256",
    "compromised accounts username and cryptographically hashed passwords",
    # PII / Identity
    "Aadhaar card number 4589 1236 7894 belonging to Rajesh Kumar, PAN card: BHYTR5421M",
    "Social security number SSN 554-12-8965, date of birth DOB 1990-05-12, residential address",
    "First name, last name, phone number, physical address, national identifier card",
    "List of patient names, phone numbers, home addresses and emails leaked",
    # Financial / Cards
    "Credit card numbers: Visa 4111111111111111, MasterCard 5500000000000000 expiration 12/28 CVV 452",
    "Bank transaction log billing invoice cardholder name card security code routing number",
    "Financial ledger balance transaction date credit debit cards account holder details",
    # Health / Medical
    "Patient medical records, medical history, diagnosis codes, prescription details for MediCare",
    "Clinical trial records, disease classification, patient health record information DOB",
    "Hospital logs, patient records, health insurance ID, drug prescription details",
    # Corporate / Other
    "Confidential CAD drawings, Apex Aerospace system designs, trade secrets NDA corporate",
    "Internal project source code repository, proprietary engineering design, confidential project plan",
    "Corporate email discussions, meeting minutes, company strategy documents, private keys",
]

SEED_LABELS = [
    "credentials", "credentials", "credentials", "credentials",
    "pii", "pii", "pii", "pii",
    "financial", "financial", "financial",
    "health", "health", "health",
    "corporate", "corporate", "corporate"
]

# Severity weight mapping (0 to 100)
SEVERITY_MAPPING = {
    "credentials": 85,
    "pii": 75,
    "financial": 95,
    "health": 90,
    "corporate": 80,
    "other": 30
}


def create_and_train_seed_model():
    """
    Trains a basic scikit-learn model on seed threat intelligence data and saves it.
    """
    try:
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=1000, stop_words='english')),
            ('clf', RandomForestClassifier(n_estimators=50, random_state=42))
        ])
        pipeline.fit(SEED_TEXTS, SEED_LABELS)
        joblib.dump(pipeline, MODEL_PATH)
        logger.info("Successfully trained and saved LeakHunter V2 seed ML model.")
        return pipeline
    except Exception as e:
        logger.error(f"Failed to train seed model: {e}")
        return None


# Global model cache to prevent disk I/O on every prediction
_cached_model = None

def get_model():
    """
    Loads model from disk or cache, training a seed model first if missing.
    """
    global _cached_model
    if _cached_model is not None:
        return _cached_model
        
    if os.path.exists(MODEL_PATH):
        try:
            _cached_model = joblib.load(MODEL_PATH)
            return _cached_model
        except Exception as e:
            logger.error(f"Error loading model from {MODEL_PATH}: {e}. Retraining...")
            
    _cached_model = create_and_train_seed_model()
    return _cached_model


def train_model(texts: list, labels: list) -> bool:
    """
    Exposes an endpoint/script function to retrain the classifier on analyst-approved datasets.
    """
    try:
        if not texts or not labels:
            return False
            
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000, stop_words='english')),
            ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
        ])
        pipeline.fit(texts, labels)
        joblib.dump(pipeline, MODEL_PATH)
        logger.info(f"Model retrained successfully on {len(texts)} samples.")
        return True
    except Exception as e:
        logger.error(f"Failed to retrain model: {e}")
        return False


def predict_leak_type(text: str) -> dict:
    """
    Predicts threat category, severity score, and model confidence for a given leak string.
    """
    if not text or len(text.strip()) < 10:
        return {
            "category": "other",
            "severity_score": 10,
            "confidence": 1.0
        }
        
    model = get_model()
    if not model:
        # Fallback heuristic if ML fails/unavailable
        text_lower = text.lower()
        if "credit card" in text_lower or "cvv" in text_lower:
            return {"category": "financial", "severity_score": 95, "confidence": 0.5}
        elif "ssn" in text_lower or "aadhaar" in text_lower or "pan card" in text_lower:
            return {"category": "pii", "severity_score": 80, "confidence": 0.5}
        elif "password" in text_lower or "hash" in text_lower:
            return {"category": "credentials", "severity_score": 85, "confidence": 0.5}
        elif "medical" in text_lower or "patient" in text_lower:
            return {"category": "health", "severity_score": 90, "confidence": 0.5}
        else:
            return {"category": "other", "severity_score": 30, "confidence": 0.5}
            
    try:
        # Predict probability
        probs = model.predict_proba([text])[0]
        classes = model.classes_
        max_idx = np.argmax(probs)
        
        category = classes[max_idx]
        confidence = float(probs[max_idx])
        
        # Calculate severity score base on category and confidence
        base_severity = SEVERITY_MAPPING.get(category, 50)
        # Scale severity based on model confidence
        severity_score = int(base_severity * (0.8 + 0.2 * confidence))
        # Cap severity at 100
        severity_score = min(max(severity_score, 0), 100)
        
        # Boost severity if specific high-risk keywords are present
        text_lower = text.lower()
        if "cvv" in text_lower or "ssn" in text_lower or "aadhaar" in text_lower:
            severity_score = min(severity_score + 10, 99)
            
        return {
            "category": category,
            "severity_score": severity_score,
            "confidence": confidence
        }
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return {
            "category": "other",
            "severity_score": 30,
            "confidence": 0.0
        }
