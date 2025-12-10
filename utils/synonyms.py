"""Column name synonym dictionary and normalization"""

from typing import Dict, List
from config import settings


# Synonym dictionary for column name normalization
COLUMN_SYNONYMS: Dict[str, List[str]] = {
    "date": ["fecha", "dt", "date:", "date_col", "period", "periodo", "dia", "day"],
    "amount": ["amt", "monto", "value", "total", "sum", "importe", "valor"],
    "description": ["desc", "descripcion", "detail", "detalle", "notes", "nota", "concepto"],
    "quantity": ["qty", "cantidad", "units", "count", "pieces", "unidades", "cant"],
    "price": ["precio", "unit_price", "rate", "tarifa", "costo", "cost"],
    "customer": ["cliente", "client", "buyer", "account", "cuenta"],
    "product": ["producto", "item", "sku", "article", "articulo"],
    "revenue": ["ingreso", "sales", "ventas", "income", "ingresos"],
    "expense": ["gasto", "cost", "costo", "egreso", "gastos"],
    "balance": ["saldo", "remaining", "outstanding", "remanente"],
    "name": ["nombre", "nm", "nombre_completo", "full_name"],
    "id": ["codigo", "code", "identifier", "clave", "numero", "number", "no", "num"],
    "month": ["mes", "monthly", "mensual"],
    "year": ["año", "anio", "yearly", "anual"],
    "category": ["categoria", "cat", "type", "tipo", "clasificacion"],
    "status": ["estado", "estatus", "situacion"],
    "comments": ["comentarios", "observaciones", "remarks", "obs"],
}


def normalize_column_name(raw_name: str) -> str:
    """
    Normalize a single column name:
    1. Lowercase
    2. Strip whitespace
    3. Replace spaces/special chars with underscore
    4. Fuzzy match to canonical synonym
    
    Args:
        raw_name: Raw column name
        
    Returns:
        Normalized column name
    """
    if not raw_name or str(raw_name).strip() == "":
        return "unnamed"
    
    # Basic normalization
    name = str(raw_name).lower().strip()
    
    # Remove special characters, keep alphanumeric and underscore
    normalized = ""
    for char in name:
        if char.isalnum():
            normalized += char
        elif char in " -_":
            normalized += "_"
    
    # Collapse multiple underscores
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    
    normalized = normalized.strip("_")
    
    if not normalized:
        return "unnamed"
    
    # Check for exact match in synonyms
    for canonical, synonyms in COLUMN_SYNONYMS.items():
        if normalized in synonyms or normalized == canonical:
            return canonical
    
    # Fuzzy match (import here to avoid circular dependency)
    from .fuzzy import fuzzy_match_column
    best_match = fuzzy_match_column(normalized, COLUMN_SYNONYMS)
    
    return best_match if best_match else normalized

