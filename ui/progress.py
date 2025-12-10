"""Progress tracking"""

from abc import ABC, abstractmethod
from typing import Optional


class ProgressTracker(ABC):
    """Abstract progress tracker"""
    
    @abstractmethod
    def start_stage(self, stage_num: int, stage_name: str):
        """Start a stage"""
        pass
    
    @abstractmethod
    def complete_stage(self, stage_num: int):
        """Complete a stage"""
        pass
    
    @abstractmethod
    def fail(self, stage_num: int, message: str):
        """Mark stage as failed"""
        pass
    
    @abstractmethod
    def complete(self):
        """Mark pipeline as complete"""
        pass


class ConsoleProgress(ProgressTracker):
    """Console-based progress tracker"""
    
    def __init__(self):
        self.stages = {
            0: "Reception",
            1: "Classification",
            2: "Structure Inference",
            3: "Data Archaeology",
            4: "Reconciliation",
            5: "Schema & ETL",
            6: "Analysis",
            7: "Output"
        }
        self.completed = set()
        self.current = None
    
    def start_stage(self, stage_num: int, stage_name: str):
        """Start a stage"""
        self.current = stage_num
        print(f"[◉] Stage {stage_num}: {stage_name}...")
    
    def complete_stage(self, stage_num: int):
        """Complete a stage"""
        self.completed.add(stage_num)
        self.current = None
        print(f"[✓] Stage {stage_num}: {self.stages.get(stage_num, 'Unknown')} complete")
    
    def fail(self, stage_num: int, message: str):
        """Mark stage as failed"""
        print(f"[✗] Stage {stage_num}: {self.stages.get(stage_num, 'Unknown')} failed - {message}")
    
    def complete(self):
        """Mark pipeline as complete"""
        print("\n[✓] Pipeline complete!")

