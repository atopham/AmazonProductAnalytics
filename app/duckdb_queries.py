import duckdb
import logging
from typing import List, Dict, Any
from .utils import handle_duckdb_error

logger = logging.getLogger(__name__)


class DuckDBQueries:
    """Class to handle all DuckDB queries for Amazon product analytics"""
    
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
    
    @handle_duckdb_error
    def load_data(self, csv_path: str) -> None:
        """
        Load CSV data into DuckDB table
        
        Args:
            csv_path: Path to the CSV file
        """
        # Drop existing table if it exists
        self.conn.execute("DROP TABLE IF EXISTS amazon_products")
        
        # Create table from CSV with proper data types
        self.conn.execute(f"""
            CREATE TABLE amazon_products AS 
            SELECT 
                asin,
                title,
                imgUrl,
                productURL,
                CAST(stars AS DOUBLE) as stars,
                CAST(reviews AS INTEGER) as reviews,
                CAST(REPLACE(CAST(price AS VARCHAR), '£', '') AS DOUBLE) as price,
                CAST(isBestSeller AS BOOLEAN) as isBestSeller,
                CAST(boughtInLastMonth AS INTEGER) as boughtInLastMonth,
                categoryName
            FROM read_csv_auto('{csv_path}')
        """)
        
        logger.info("Data loaded successfully into DuckDB")
    
    @handle_duckdb_error
    def get_category_stats(self) -> List[Dict[str, Any]]:
        """
        Calculate average, standard deviation, and variance for each category
        
        Returns:
            List of dictionaries with category statistics
        """
        query = """
            SELECT 
                categoryName as category_name,
                AVG(stars) as average_rating,
                STDDEV(stars) as standard_deviation,
                VAR_POP(stars) as variance,
                COUNT(*) as product_count
            FROM amazon_products 
            WHERE stars IS NOT NULL AND categoryName IS NOT NULL
            GROUP BY categoryName
            HAVING COUNT(*) >= 10  -- Only include categories with at least 10 products
            ORDER BY average_rating DESC
        """
        
        result = self.conn.execute(query).fetchall()
        columns = ['category_name', 'average_rating', 'standard_deviation', 'variance', 'product_count']
        
        return [dict(zip(columns, row)) for row in result]
    
    @handle_duckdb_error
    def get_z_score_outliers(self, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Identify categories with statistically significant high or low average ratings
        
        Args:
            threshold: Z-score threshold (default: 2.0)
            
        Returns:
            List of dictionaries with z-score outlier information
        """
        query = f"""
            WITH category_stats AS (
                SELECT 
                    categoryName,
                    AVG(stars) as avg_rating,
                    COUNT(*) as product_count
                FROM amazon_products 
                WHERE stars IS NOT NULL AND categoryName IS NOT NULL
                GROUP BY categoryName
                HAVING COUNT(*) >= 10
            ),
            category_distribution AS (
                SELECT 
                    AVG(avg_rating) as category_avg,
                    STDDEV(avg_rating) as category_stddev
                FROM category_stats
            )
            SELECT 
                cs.categoryName as category_name,
                cs.avg_rating as average_rating,
                (cs.avg_rating - cd.category_avg) / cd.category_stddev as z_score,
                cd.category_avg as global_average,
                cs.product_count
            FROM category_stats cs
            CROSS JOIN category_distribution cd
            WHERE ABS((cs.avg_rating - cd.category_avg) / cd.category_stddev) >= {threshold}
            ORDER BY ABS((cs.avg_rating - cd.category_avg) / cd.category_stddev) DESC
        """
        
        result = self.conn.execute(query).fetchall()
        columns = ['category_name', 'average_rating', 'z_score', 'global_average', 'product_count']
        
        formatted_results = []
        for row in result:
            z_score = row[2]
            formatted_results.append({
                'category_name': row[0],
                'average_rating': row[1],
                'z_score': z_score,
                'global_average': row[3],
                'product_count': row[4],
                'is_high_outlier': z_score > threshold,
                'is_low_outlier': z_score < -threshold
            })
        
        return formatted_results
    
    @handle_duckdb_error
    def get_high_variability_categories(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get categories with highest rating variability
        
        Args:
            limit: Number of categories to return (default: 20)
            
        Returns:
            List of dictionaries with high variability categories
        """
        query = f"""
            SELECT 
                categoryName as category_name,
                STDDEV(stars) as standard_deviation,
                VAR_POP(stars) as variance,
                AVG(stars) as average_rating,
                COUNT(*) as product_count
            FROM amazon_products 
            WHERE stars IS NOT NULL AND categoryName IS NOT NULL
            GROUP BY categoryName
            HAVING COUNT(*) >= 10
            ORDER BY STDDEV(stars) DESC
            LIMIT {limit}
        """
        
        result = self.conn.execute(query).fetchall()
        columns = ['category_name', 'standard_deviation', 'variance', 'average_rating', 'product_count']
        
        return [dict(zip(columns, row)) for row in result]
    
    @handle_duckdb_error
    def get_low_variability_categories(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get categories with lowest rating variability
        
        Args:
            limit: Number of categories to return (default: 20)
            
        Returns:
            List of dictionaries with low variability categories
        """
        query = f"""
            SELECT 
                categoryName as category_name,
                STDDEV(stars) as standard_deviation,
                VAR_POP(stars) as variance,
                AVG(stars) as average_rating,
                COUNT(*) as product_count
            FROM amazon_products 
            WHERE stars IS NOT NULL AND categoryName IS NOT NULL
            GROUP BY categoryName
            HAVING COUNT(*) >= 10
            ORDER BY STDDEV(stars) ASC
            LIMIT {limit}
        """
        
        result = self.conn.execute(query).fetchall()
        columns = ['category_name', 'standard_deviation', 'variance', 'average_rating', 'product_count']
        
        return [dict(zip(columns, row)) for row in result]
    
    @handle_duckdb_error
    def get_global_stats(self) -> Dict[str, Any]:
        """
        Get global statistics for the entire dataset
        
        Returns:
            Dictionary with global statistics
        """
        query = """
            SELECT 
                COUNT(*) as total_products,
                COUNT(DISTINCT categoryName) as total_categories,
                AVG(stars) as global_avg_rating,
                STDDEV(stars) as global_stddev,
                MIN(stars) as min_rating,
                MAX(stars) as max_rating
            FROM amazon_products 
            WHERE stars IS NOT NULL AND categoryName IS NOT NULL
        """
        
        result = self.conn.execute(query).fetchone()
        columns = ['total_products', 'total_categories', 'global_avg_rating', 
                  'global_stddev', 'min_rating', 'max_rating']
        
        return dict(zip(columns, result))
    
    @handle_duckdb_error
    def get_category_distribution(self) -> List[Dict[str, Any]]:
        """
        Get distribution of products across categories
        
        Returns:
            List of dictionaries with category distribution
        """
        query = """
            SELECT 
                categoryName as category_name,
                COUNT(*) as product_count,
                AVG(stars) as avg_rating,
                MIN(stars) as min_rating,
                MAX(stars) as max_rating
            FROM amazon_products 
            WHERE categoryName IS NOT NULL
            GROUP BY categoryName
            ORDER BY product_count DESC
        """
        
        result = self.conn.execute(query).fetchall()
        columns = ['category_name', 'product_count', 'avg_rating', 'min_rating', 'max_rating']
        
        return [dict(zip(columns, row)) for row in result] 