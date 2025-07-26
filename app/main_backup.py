from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import duckdb
import logging
import os
from typing import List, Optional
from contextlib import asynccontextmanager

from .models import CategoryStats, ZScoreOutlier, VariabilityCategory, APIResponse
from .duckdb_queries import DuckDBQueries
from .utils import validate_data_quality, optimize_queries

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for database connection
db_conn = None
db_queries = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    global db_conn, db_queries
    
    try:
        # Initialize DuckDB connection
        db_conn = duckdb.connect(':memory:')
        db_queries = DuckDBQueries(db_conn)
        
        # Load data from CSV
        csv_path = "data/amz_uk_processed_data.csv"
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found at {csv_path}")
        
        logger.info("Loading data into DuckDB...")
        db_queries.load_data(csv_path)
        
        # Validate data quality
        quality_stats = validate_data_quality(db_conn)
        logger.info(f"Data quality stats: {quality_stats}")
        
        # Apply query optimizations
        optimize_queries(db_conn)
        
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        if db_conn:
            db_conn.close()
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Create FastAPI app
app = FastAPI(
    title="Amazon Product Analytics API",
    description="FastAPI application for analyzing Amazon UK product categories using DuckDB",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=APIResponse)
async def root():
    """Root endpoint with API information"""
    return APIResponse(
        success=True,
        message="Amazon Product Analytics API",
        data=[
            {
                "endpoints": [
                    "/category-stats",
                    "/z-score-outliers",
                    "/high-variability",
                    "/low-variability",
                    "/global-stats",
                    "/category-distribution"
                ],
                "docs": "/docs"
            }
        ]
    )


@app.get("/category-stats", response_model=List[CategoryStats])
async def get_category_stats():
    """
    Get average, standard deviation, and variance for each product category.
    
    Returns:
        List of category statistics including average rating, standard deviation, 
        variance, and product count for each category.
    """
    try:
        if not db_queries:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        results = db_queries.get_category_stats()
        return [CategoryStats(**result) for result in results]
        
    except Exception as e:
        logger.error(f"Error in category-stats endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/z-score-outliers", response_model=List[ZScoreOutlier])
async def get_z_score_outliers(
    threshold: float = Query(default=2.0, ge=0.0, le=5.0, description="Z-score threshold")
):
    """
    Identify categories with statistically significant high or low average ratings.
    
    Args:
        threshold: Z-score threshold (default: 2.0, range: 0.0-5.0)
    
    Returns:
        List of categories with z-scores above the threshold, indicating 
        statistically significant deviations from the global average.
    """
    try:
        if not db_queries:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        results = db_queries.get_z_score_outliers(threshold)
        return [ZScoreOutlier(**result) for result in results]
        
    except Exception as e:
        logger.error(f"Error in z-score-outliers endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/high-variability", response_model=List[VariabilityCategory])
async def get_high_variability_categories(
    limit: int = Query(default=20, ge=1, le=100, description="Number of categories to return")
):
    """
    Get categories with the highest rating variability.
    
    Args:
        limit: Number of categories to return (default: 20, range: 1-100)
    
    Returns:
        List of categories ordered by highest standard deviation of ratings.
    """
    try:
        if not db_queries:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        results = db_queries.get_high_variability_categories(limit)
        return [VariabilityCategory(**result) for result in results]
        
    except Exception as e:
        logger.error(f"Error in high-variability endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/low-variability", response_model=List[VariabilityCategory])
async def get_low_variability_categories(
    limit: int = Query(default=20, ge=1, le=100, description="Number of categories to return")
):
    """
    Get categories with the lowest rating variability.
    
    Args:
        limit: Number of categories to return (default: 20, range: 1-100)
    
    Returns:
        List of categories ordered by lowest standard deviation of ratings.
    """
    try:
        if not db_queries:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        results = db_queries.get_low_variability_categories(limit)
        return [VariabilityCategory(**result) for result in results]
        
    except Exception as e:
        logger.error(f"Error in low-variability endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/global-stats", response_model=APIResponse)
async def get_global_stats():
    """
    Get global statistics for the entire dataset.
    
    Returns:
        Global statistics including total products, categories, average rating, etc.
    """
    try:
        if not db_queries:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        results = db_queries.get_global_stats()
        return APIResponse(
            success=True,
            message="Global statistics retrieved successfully",
            data=[results]
        )
        
    except Exception as e:
        logger.error(f"Error in global-stats endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/category-distribution", response_model=APIResponse)
async def get_category_distribution():
    """
    Get distribution of products across categories.
    
    Returns:
        Distribution of products across all categories with statistics.
    """
    try:
        if not db_queries:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        results = db_queries.get_category_distribution()
        return APIResponse(
            success=True,
            message="Category distribution retrieved successfully",
            data=results
        )
        
    except Exception as e:
        logger.error(f"Error in category-distribution endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 