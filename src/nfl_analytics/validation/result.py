from dataclasses import dataclass

#This gives every rule the same return shape

@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    message: str

    @staticmethod
    def ok() -> "ValidationResult":
        return ValidationResult(True, "SQL is valid.")

    @staticmethod
    def fail(message: str) -> "ValidationResult":
        return ValidationResult(False, message)