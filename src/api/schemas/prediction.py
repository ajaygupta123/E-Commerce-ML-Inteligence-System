"""Prediction API schemas."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class PredictionRequest(BaseModel):
    """Request for discount prediction.
    
    Fields match the training dataset columns:
    - actual_price: Product price (optional, but highly recommended for accuracy)
    - category: Product category (required)
    - rating: Product rating (optional, 0-5)
    - rating_count: Number of reviews (optional)
    - product_name: Product name (optional)
    - about_product: Product description (optional)
    
    Note: actual_price is optional but strongly recommended as it's a key feature.
    If not provided, the model will use a default value which may reduce prediction accuracy.
    """
    actual_price: Optional[float] = Field(None, gt=0, description="Product actual price (optional but recommended)")
    category: str = Field(..., min_length=1, description="Product category")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Product rating")
    rating_count: Optional[int] = Field(None, ge=0, description="Number of reviews/ratings")
    product_name: Optional[str] = Field(None, description="Product name")
    about_product: Optional[str] = Field(None, description="Product description")
    # Additional optional fields that may be in dataset
    discounted_price: Optional[float] = Field(None, gt=0, description="Discounted price (if known)")
    img_link: Optional[str] = Field(None, description="Product image link")
    product_link: Optional[str] = Field(None, description="Product link")


class PredictionResponse(BaseModel):
    """Response with discount prediction."""
    predicted_discount: float = Field(..., ge=0, le=100, description="Predicted discount percentage")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence score")
    features: Dict[str, Any] = Field(..., description="Input features used")


class ExplanationResponse(BaseModel):
    """Response with SHAP explanation."""
    predicted_discount: float
    confidence_score: float
    explanation: Dict[str, Any] = Field(..., description="SHAP explanation values")
    features: Dict[str, Any]


