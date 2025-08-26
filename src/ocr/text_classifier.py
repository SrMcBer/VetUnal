import unicodedata
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Dict, Tuple

class PageType(Enum):
    UNKNOWN = auto()
    HISTORIA_CLINICA = auto()
    CEDULA = auto()
    RECIBO = auto()

    def __str__(self):
        return self.name.replace("_", " ")


@dataclass
class ClassificationResult:
    """Enhanced result that includes classification criteria"""
    page_type: PageType
    matched_indicators: List[str]
    confidence_score: float = 0.0

@dataclass
class PageInfo:
    """Enhanced PageInfo with classification details"""
    page_number: int
    page_type: PageType
    text: str
    matched_indicators: List[str]
    confidence_score: float = 0.0

def normalize_string(s: str) -> str:
    s = s.lower()
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('utf-8')
    return s

class TextClassifier:
    def __init__(self):
        self.historia_indicators = [
            "proceso salud", "historia clinica", "caninas", "datos del paciente",
            "origen y procedencia", "de la fauna"
        ]
        self.cedula_indicators = [
            "cedula de", "de colombia", "nacionalidad", "nuip",
            "indice derecho", "registraduria civil","de expedicion","NACIONAL"
        ]
        self.recibo_indicators = [
            "enel", "consumo", "de la cuenta", "factura", "suspension", "pago",
            "oportuno", "vanti", "referencia", "cuenta", "contrato",
            "para pagos", "predio","comportamiento","valor","periodo","medidor",
            "corresponsal bancario","lectura","servicio","suspension",
            # "$" We could add this but it might be too generic and generate false positives
        ]
    
    def classify_page(self, text: str) -> ClassificationResult:
        """
        Classify page and return detailed results including matched indicators
        """
        norm = normalize_string(text)
        
        # Find all matching indicators for each category
        historia_matches = [ind for ind in self.historia_indicators if ind in norm]
        cedula_matches = [ind for ind in self.cedula_indicators if ind in norm]
        recibo_matches = [ind for ind in self.recibo_indicators if ind in norm]
        
        # Determine classification based on matches
        if historia_matches:
            confidence = len(historia_matches) / len(self.historia_indicators)
            return ClassificationResult(
                page_type=PageType.HISTORIA_CLINICA,
                matched_indicators=historia_matches,
                confidence_score=confidence
            )
        elif cedula_matches:
            confidence = len(cedula_matches) / len(self.cedula_indicators)
            return ClassificationResult(
                page_type=PageType.CEDULA,
                matched_indicators=cedula_matches,
                confidence_score=confidence
            )
        elif recibo_matches:
            confidence = len(recibo_matches) / len(self.recibo_indicators)
            return ClassificationResult(
                page_type=PageType.RECIBO,
                matched_indicators=recibo_matches,
                confidence_score=confidence
            )
        else:
            return ClassificationResult(
                page_type=PageType.UNKNOWN,
                matched_indicators=[],
                confidence_score=0.0
            )

    def get_detailed_classification(self, text: str) -> dict:
        """
        Get detailed breakdown of all potential matches across categories
        """
        norm = normalize_string(text)
        
        return {
            "historia_matches": [ind for ind in self.historia_indicators if ind in norm],
            "cedula_matches": [ind for ind in self.cedula_indicators if ind in norm],
            "recibo_matches": [ind for ind in self.recibo_indicators if ind in norm],
            "normalized_text": norm,
            "original_text": text
        }
