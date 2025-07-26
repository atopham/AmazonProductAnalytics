# Amazon Product Analytics API

A FastAPI application for analyzing Amazon UK product categories using DuckDB. This application provides insights into product ratings, category performance, and statistical outliers.

## Features

- **Automatic Data Download**: Downloads Amazon UK product data from KaggleHub automatically
- **Smart Caching**: Uses persistent DuckDB database for fast subsequent runs
- **Statistical Analysis**: Z-score outliers, category variability, and global statistics
- **RESTful API**: Easy-to-use endpoints for data analysis
- **Real-time Analytics**: Fast query performance with DuckDB
- **Docker Support**: Multiple deployment options for different use cases

## Quick Start

### Prerequisites

- Python 3.11+ (3.13 recommended)
- pip

### Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd AmazonProductAnalytics
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   uvicorn app.main:app --reload
   ```

The application will automatically:
- Download the Amazon UK products dataset from KaggleHub
- Cache the data locally for future use
- Create a persistent DuckDB database
- Start the API server

### First Run

On the first run, the application will download approximately 2.2 million product records from KaggleHub. This may take a few minutes depending on your internet connection.

## Docker Deployment

### Option 1: In-Memory Database (Default - Recommended for Testing)

Fast startup with no persistent storage - data is downloaded fresh each time:

```bash
docker-compose up --build
```

**Pros**: 
- Fast startup
- No storage requirements
- Clean environment each time

**Cons**: 
- Data downloaded on each restart
- No persistence between restarts

### Option 2: Persistent Database (Recommended for Production)

Persistent storage with volume mounts for data and database:

```bash
# Create data directory
mkdir -p data

# Run with persistent storage
USE_PERSISTENT_DB=true docker-compose up --build
```

**Pros**: 
- Fast subsequent starts
- Data persistence between restarts
- Production-ready

**Cons**: 
- Requires disk space (~2-3GB)
- Initial startup takes longer

### Option 3: Read-Only Data Mount

If you have pre-downloaded data:

```bash
# Place your CSV file in data/amz_uk_processed_data.csv
# Then run with read-only mount
docker-compose up --build
```

### Environment Variables

You can control the Docker behavior using environment variables:

```bash
# In-memory database (default)
docker-compose up --build

# Persistent database
USE_PERSISTENT_DB=true docker-compose up --build

# Or set it in your shell
export USE_PERSISTENT_DB=true
docker-compose up --build
```

### Docker Environment Detection

The application automatically detects Docker environments and:
- Uses in-memory databases when persistent storage isn't available
- Provides appropriate logging for Docker deployments
- Handles read-only filesystems gracefully

## API Endpoints

### Core Analytics

- `GET /` - API information and available endpoints
- `GET /category-stats` - Category statistics (average rating, standard deviation, etc.)
- `GET /z-score-outliers?threshold=1.75` - Statistical outliers based on z-scores
- `GET /high-variability` - Categories with highest rating variability
- `GET /low-variability` - Categories with lowest rating variability
- `GET /global-stats` - Global statistics across all products
- `GET /category-distribution` - Distribution of products across categories

### Cache Management

- `GET /cache-info` - Information about cached data and database
- `POST /clear-cache` - Clear all cached data and recreate database

### Interactive Documentation

- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

## Data Management

### Automatic Data Download

The application uses KaggleHub to automatically download the Amazon UK products dataset:
- **Dataset**: `asaniczka/amazon-uk-products-dataset-2023`
- **Size**: ~2.2 million products across 296 categories
- **Caching**: Data is cached locally in the `data/` directory

### Database Caching

- **Persistent Database**: Uses `data/amazon_products.db` for fast subsequent runs
- **In-Memory Database**: Falls back to in-memory when persistent storage isn't available
- **Automatic Recovery**: Recreates database if corrupted or missing

### Cache Management

```bash
# Check cache status
curl http://localhost:8000/cache-info

# Clear cache and redownload data
curl -X POST http://localhost:8000/clear-cache
```

## Configuration

### Environment Variables

- `DATA_DIR`: Directory for data storage (default: `data`)
- `DB_PATH`: Path to DuckDB database (default: `data/amazon_products.db`)
- `USE_PERSISTENT_DB`: Use persistent database (default: `true`)
- `DOCKER_CONTAINER`: Set to `true` in Docker environments

### Data Sources

The application automatically downloads data from:
- **Primary**: KaggleHub dataset `asaniczka/amazon-uk-products-dataset-2023`
- **Fallback**: Local CSV file (if available)

## Data Schema

The dataset contains the following fields:
- `asin`: Amazon Standard Identification Number
- `title`: Product title
- `imgUrl`: Product image URL
- `productURL`: Product page URL
- `stars`: Product rating (0-5)
- `reviews`: Number of reviews
- `price`: Product price in GBP
- `isBestSeller`: Whether product is a best seller
- `boughtInLastMonth`: Number of purchases in last month
- `categoryName`: Product category

## Statistical Analysis

### Z-Score Outliers

Identifies categories with statistically significant deviations from the mean:
- **Threshold 1.0**: Moderately significant outliers
- **Threshold 1.5**: More significant outliers
- **Threshold 2.0**: Extremely significant outliers (rare in this dataset)

### Category Variability

Analyzes rating consistency across categories:
- **High Variability**: Categories with inconsistent ratings
- **Low Variability**: Categories with consistent ratings

## Performance

### Local Development
- **First Run**: ~2-5 minutes (data download + database creation)
- **Subsequent Runs**: ~10-30 seconds (database loading)
- **Query Performance**: Sub-second response times for most analytics

### Docker Deployment
- **In-Memory Mode**: ~2-5 minutes per restart (fresh data download)
- **Persistent Mode**: ~10-30 seconds after first run
- **Query Performance**: Sub-second response times

## Troubleshooting

### Common Issues

1. **KaggleHub Download Fails**:
   - Check internet connection
   - Verify KaggleHub access
   - Try clearing cache: `POST /clear-cache`

2. **Database Errors**:
   - Clear cache to recreate database
   - Check disk space
   - Verify file permissions

3. **Docker Storage Issues**:
   - Use in-memory mode: `docker-compose up`
   - Use persistent mode: `USE_PERSISTENT_DB=true docker-compose up`
   - Check volume mount permissions

4. **Memory Issues**:
   - Use persistent database mode
   - Increase system memory
   - Consider using smaller data subsets

### Logs

The application provides detailed logging:
- Data download progress
- Database operations
- Query performance
- Error details
- Docker environment detection

## Development

### Project Structure

```
AmazonProductAnalytics/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── data_manager.py      # Data download and caching
│   ├── duckdb_queries.py    # Database queries
│   ├── models.py            # Pydantic models
│   └── utils.py             # Utility functions
├── data/                    # Cached data directory
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # In-memory Docker setup
├── docker-compose.persistent.yml  # Persistent Docker setup
├── README.md               # This file
└── .gitignore
```

### Adding New Analytics

1. Add query method to `DuckDBQueries` class
2. Create Pydantic model in `models.py`
3. Add endpoint in `main.py`
4. Update documentation

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here] 