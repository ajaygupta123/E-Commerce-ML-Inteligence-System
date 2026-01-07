"""Custom exceptions for the application."""


class EcommerceException(Exception):
    """Base exception for e-commerce system."""
    pass


class ModelNotFoundError(EcommerceException):
    """Raised when ML model file is not found."""
    pass


class DatabaseError(EcommerceException):
    """Raised when database operation fails."""
    pass


class ValidationError(EcommerceException):
    """Raised when input validation fails."""
    pass


class CacheError(EcommerceException):
    """Raised when cache operation fails."""
    pass


class LLMError(EcommerceException):
    """Raised when LLM service fails."""
    pass




