"""Pipeline stages"""

from .s0_reception import Receiver
from .s1_classification import Classifier
from .s2_structure import StructureInferrer
from .s3_archaeology import Archaeologist
from .s4_reconciliation import Reconciler
from .s5_etl import ETLManager
from .s6_analysis import Analyzer
from .s7_output import OutputManager

__all__ = [
    "Receiver",
    "Classifier",
    "StructureInferrer",
    "Archaeologist",
    "Reconciler",
    "ETLManager",
    "Analyzer",
    "OutputManager",
]

