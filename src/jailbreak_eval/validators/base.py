from abc import ABC, abstractmethod

from jailbreak_eval.schema import EvaluationCase, ValidationResult


class Validator(ABC):
    """Common interface for every baseline and proposed validator."""

    name: str

    @abstractmethod
    def evaluate(self, case: EvaluationCase) -> ValidationResult:
        """Evaluate one case and return a standardised result."""
        raise NotImplementedError
