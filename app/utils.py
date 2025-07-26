import logging
from typing import List, Dict, Any
import duckdb
import pandas as pd


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_data_quality(conn: duckdb.DuckDBPyConnection) -> Dict[str, Any]:
    """
    Validate data quality and return summary statistics
    
    Args:
        conn: DuckDB connection
        
    Returns:
        Dictionary with data quality metrics
    """
    try:
        # Check total row count
        total_rows = conn.execute("SELECT COUNT(*) FROM amazon_products").fetchone()[0]
        
        # Check for null values in critical columns
        null_stats = conn.execute("""
            SELECT 
                COUNT(*) as total_rows,
                SUM(CASE WHEN stars IS NULL THEN 1 ELSE 0 END) as null_stars,
                SUM(CASE WHEN categoryName IS NULL THEN 1 ELSE 0 END) as null_categories,
                SUM(CASE WHEN stars IS NOT NULL AND categoryName IS NOT NULL THEN 1 ELSE 0 END) as valid_rows
            FROM amazon_products
        """).fetchone()
        
        # Check rating range
        rating_range = conn.execute("""
            SELECT MIN(stars), MAX(stars), AVG(stars)
            FROM amazon_products 
            WHERE stars IS NOT NULL
        """).fetchone()
        
        # Count unique categories
        category_count = conn.execute("""
            SELECT COUNT(DISTINCT categoryName) 
            FROM amazon_products 
            WHERE categoryName IS NOT NULL
        """).fetchone()[0]
        
        return {
            "total_rows": total_rows,
            "valid_rows": null_stats[3],
            "null_stars": null_stats[1],
            "null_categories": null_stats[2],
            "min_rating": rating_range[0],
            "max_rating": rating_range[1],
            "avg_rating": rating_range[2],
            "unique_categories": category_count
        }
        
    except Exception as e:
        logger.error(f"Error validating data quality: {e}")
        raise


def optimize_queries(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Apply query optimizations for better performance
    
    Args:
        conn: DuckDB connection
    """
    try:
        # Analyze table for better query planning (safer than creating indexes)
        conn.execute("ANALYZE amazon_products")
        
        logger.info("Query optimizations applied successfully")
        
    except Exception as e:
        logger.warning(f"Could not apply all optimizations: {e}")


def format_response_data(data: List[tuple], columns: List[str]) -> List[Dict[str, Any]]:
    """
    Format query results into list of dictionaries
    
    Args:
        data: Query results as list of tuples
        columns: Column names
        
    Returns:
        List of dictionaries with formatted data
    """
    return [dict(zip(columns, row)) for row in data]


def handle_duckdb_error(func):
    """
    Decorator to handle DuckDB errors gracefully
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function with error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except duckdb.Error as e:
            logger.error(f"DuckDB error in {func.__name__}: {e}")
            raise Exception(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise
    return wrapper 