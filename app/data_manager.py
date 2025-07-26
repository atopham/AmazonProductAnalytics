import os
import logging
import duckdb
from pathlib import Path
import kagglehub

logger = logging.getLogger(__name__)


class DataManager:
    """Manages data downloading, caching, and database operations"""
    
    def __init__(self, data_dir: str = "data", db_path: str = "data/amazon_products.db"):
        self.data_dir = Path(data_dir)
        self.db_path = Path(db_path)
        self.csv_path = self.data_dir / "amz_uk_processed_data.csv"
        
        # Detect if we're in a Docker environment
        self.is_docker = self._detect_docker_environment()
        
        # Ensure data directory exists (only if not in Docker or if directory is writable)
        if not self.is_docker or self._is_directory_writable(self.data_dir):
            self.data_dir.mkdir(exist_ok=True)
    
    def _detect_docker_environment(self) -> bool:
        """Detect if running in a Docker container"""
        # Check for common Docker indicators
        docker_indicators = [
            "/.dockerenv",  # Docker creates this file
            "/proc/1/cgroup",  # Check cgroup for docker
        ]
        
        for indicator in docker_indicators:
            if os.path.exists(indicator):
                return True
        
        # Check environment variables
        if os.environ.get("DOCKER_CONTAINER") == "true":
            return True
        
        return False
    
    def _is_directory_writable(self, directory: Path) -> bool:
        """Check if a directory is writable"""
        try:
            test_file = directory / ".test_write"
            test_file.touch()
            test_file.unlink()
            return True
        except (OSError, PermissionError):
            return False
    
    def get_data_path(self) -> Path:
        """
        Get the path to the data file, downloading if necessary
        
        Returns:
            Path to the CSV data file
        """
        if self.csv_path.exists():
            logger.info(f"Using cached data at {self.csv_path}")
            return self.csv_path
        
        logger.info("Data not found locally, downloading from KaggleHub...")
        return self._download_data()
    
    def _download_data(self) -> Path:
        """
        Download data from KaggleHub
        
        Returns:
            Path to the downloaded CSV file
        """
        try:
            # Download the dataset from KaggleHub
            dataset_path = kagglehub.dataset_download("asaniczka/amazon-uk-products-dataset-2023")
            
            # Find the CSV file in the downloaded dataset
            csv_files = list(Path(dataset_path).glob("*.csv"))
            
            if not csv_files:
                raise FileNotFoundError("No CSV files found in the downloaded dataset")
            
            # Use the first CSV file found
            source_csv = csv_files[0]
            
            # In Docker, we might not be able to write to the data directory
            if self.is_docker and not self._is_directory_writable(self.data_dir):
                logger.warning("Running in Docker with read-only filesystem, using in-memory data")
                return source_csv
            
            # Copy to our data directory
            import shutil
            shutil.copy2(source_csv, self.csv_path)
            
            logger.info(f"Data downloaded successfully to {self.csv_path}")
            return self.csv_path
            
        except Exception as e:
            logger.error(f"Failed to download data from KaggleHub: {e}")
            raise Exception(f"Data download failed: {str(e)}")
    
    def get_database_connection(self, use_persistent_db: bool = True) -> duckdb.DuckDBPyConnection:
        """
        Get a DuckDB connection, using persistent database if available
        
        Args:
            use_persistent_db: Whether to use persistent database (default: True)
            
        Returns:
            DuckDB connection
        """
        # Check environment variable for Docker deployments
        env_use_persistent = os.environ.get('USE_PERSISTENT_DB', 'true').lower() == 'true'
        use_persistent_db = use_persistent_db and env_use_persistent
        
        # In Docker, check if we can use persistent storage
        if self.is_docker and use_persistent_db:
            if not self._is_directory_writable(self.db_path.parent):
                logger.info("Docker environment detected with read-only filesystem, using in-memory database")
                use_persistent_db = False
        
        if use_persistent_db and self.db_path.exists():
            try:
                logger.info(f"Using persistent database at {self.db_path}")
                conn = duckdb.connect(str(self.db_path))
                
                # Check if the table exists and has data
                result = conn.execute("SELECT COUNT(*) FROM amazon_products").fetchone()
                if result[0] > 0:
                    logger.info(f"Database contains {result[0]} records")
                    return conn
                else:
                    logger.warning("Database exists but is empty, will reload data")
                    conn.close()
            except Exception as e:
                logger.warning(f"Database exists but cannot be accessed: {e}, will reload data")
                try:
                    conn.close()
                except:
                    pass
        
        # Create new database and load data
        if use_persistent_db:
            logger.info("Creating new persistent database and loading data...")
            conn = duckdb.connect(str(self.db_path))
        else:
            logger.info("Creating new in-memory database and loading data...")
            conn = duckdb.connect(":memory:")
        
        # Load data into database
        self._load_data_into_db(conn)
        
        return conn
    
    def _load_data_into_db(self, conn: duckdb.DuckDBPyConnection) -> None:
        """
        Load CSV data into DuckDB table
        
        Args:
            conn: DuckDB connection
        """
        csv_path = self.get_data_path()
        
        # Drop existing table if it exists
        conn.execute("DROP TABLE IF EXISTS amazon_products")
        
        # Create table from CSV with proper data types
        conn.execute(f"""
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
        
        # Get row count for logging
        row_count = conn.execute("SELECT COUNT(*) FROM amazon_products").fetchone()[0]
        logger.info(f"Loaded {row_count} records into database")
    
    def clear_cache(self) -> None:
        """Clear all cached data and database"""
        try:
            if self.csv_path.exists():
                self.csv_path.unlink()
                logger.info("Cleared CSV cache")
            
            if self.db_path.exists():
                self.db_path.unlink()
                logger.info("Cleared database cache")
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def get_cache_info(self) -> dict:
        """Get information about cached data"""
        # Check environment variable for Docker deployments
        env_use_persistent = os.environ.get('USE_PERSISTENT_DB', 'true').lower() == 'true'
        
        info = {
            "csv_exists": self.csv_path.exists(),
            "db_exists": self.db_path.exists(),
            "csv_size_mb": 0,
            "db_size_mb": 0,
            "record_count": 0,
            "is_docker": self.is_docker,
            "use_persistent_db": env_use_persistent and self._is_directory_writable(self.db_path.parent) if self.is_docker else True
        }
        
        if self.csv_path.exists():
            info["csv_size_mb"] = round(self.csv_path.stat().st_size / (1024 * 1024), 2)
        
        if self.db_path.exists():
            info["db_size_mb"] = round(self.db_path.stat().st_size / (1024 * 1024), 2)
            
            try:
                conn = duckdb.connect(str(self.db_path))
                result = conn.execute("SELECT COUNT(*) FROM amazon_products").fetchone()
                info["record_count"] = result[0]
                conn.close()
            except Exception:
                pass
        
        return info 