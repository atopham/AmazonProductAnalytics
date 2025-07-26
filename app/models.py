from pydantic import BaseModel
from typing import List, Optional


class CategoryStats(BaseModel):
    """Model for category statistics response"""
    category_name: str
    average_rating: float
    standard_deviation: float
    variance: float
    product_count: int


class ZScoreOutlier(BaseModel):
    """Model for z-score outlier response"""
    category_name: str
    average_rating: float
    z_score: float
    global_average: float
    is_high_outlier: bool
    is_low_outlier: bool


class VariabilityCategory(BaseModel):
    """Model for high/low variability categories response"""
    category_name: str
    standard_deviation: float
    variance: float
    average_rating: float
    product_count: int


class APIResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    message: str
    data: Optional[List] = None
    error: Optional[str] = None 