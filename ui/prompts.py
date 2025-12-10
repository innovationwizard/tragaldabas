"""User interaction prompts"""

from abc import ABC, abstractmethod
from core.enums import Domain


class UserPrompt(ABC):
    """Abstract user prompt interface"""
    
    @abstractmethod
    async def yes_no(self, question: str) -> bool:
        """Ask yes/no question"""
        pass
    
    @abstractmethod
    async def select_domain(self) -> Domain:
        """Select domain"""
        pass


class ConsolePrompt(UserPrompt):
    """Console-based user prompts"""
    
    async def yes_no(self, question: str) -> bool:
        """Ask yes/no question"""
        while True:
            response = input(f"{question} (Y/N): ").strip().upper()
            if response in ['Y', 'YES']:
                return True
            elif response in ['N', 'NO']:
                return False
            else:
                print("Please enter Y or N")
    
    async def select_domain(self) -> Domain:
        """Select domain"""
        print("\nAvailable domains:")
        for i, domain in enumerate(Domain, 1):
            print(f"  {i}. {domain.value}")
        
        while True:
            try:
                choice = int(input("Select domain (1-6): "))
                if 1 <= choice <= len(Domain):
                    return list(Domain)[choice - 1]
                else:
                    print("Invalid choice")
            except ValueError:
                print("Please enter a number")

