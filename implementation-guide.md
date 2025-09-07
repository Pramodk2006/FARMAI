# Agricultural AI System - Implementation Guide

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Database Setup](#database-setup)
7. [API Configuration](#api-configuration)
8. [Deployment](#deployment)
9. [Testing](#testing)
10. [Monitoring](#monitoring)
11. [Maintenance](#maintenance)
12. [Troubleshooting](#troubleshooting)

## System Overview

The Agricultural AI System is a comprehensive platform that integrates farmer profiles, real-time external data, and computed analytics to provide actionable insights for agricultural decision-making. The system employs progressive profiling to gradually collect farmer data while providing immediate value.

### Key Features

- **Progressive Profiling**: Gradual data collection to reduce farmer onboarding friction
- **Real-time Data Integration**: Weather, market prices, satellite imagery, pest alerts
- **Hybrid Data Management**: Soil health monitoring and rainfall pattern analysis
- **Automated Data Collection**: Scheduled collection from multiple sources
- **RESTful API**: Comprehensive endpoints for data access and management
- **Scalable Architecture**: Designed for growth and high availability

### Technology Stack

- **Backend**: Python 3.8+, FastAPI, Motor (AsyncIO MongoDB driver)
- **Database**: MongoDB for document storage
- **External APIs**: Weather, market, satellite, pest, government schemes
- **Async Processing**: AsyncIO for concurrent operations
- **Testing**: Pytest with async support
- **Deployment**: Docker containers, Uvicorn ASGI server

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Server                       │
├─────────────────────────────────────────────────────────┤
│                 Data Coordinator                        │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │
│  │   MongoDB   │ │ Real-time   │ │    Hybrid Data      │ │
│  │   Setup     │ │  Fetchers   │ │    Managers         │ │
│  └─────────────┘ └─────────────┘ └─────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐ ┌─────────────────────┐ │
│  │  Progressive Workflow       │ │  Automated Data     │ │
│  │  Manager                    │ │  Collector          │ │
│  └─────────────────────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Registration**: Farmers register with minimal information
2. **Progressive Profiling**: System gradually collects additional data
3. **Real-time Data Collection**: Automated fetching from external APIs
4. **Data Processing**: Hybrid managers analyze soil health and rainfall patterns
5. **Insights Generation**: Data coordinator provides actionable recommendations
6. **Continuous Monitoring**: Automated collection and alert systems

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS, or Windows 10+
- **Python**: Version 3.8 or higher
- **MongoDB**: Version 4.4 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: At least 20GB available space
- **Network**: Stable internet connection for external API access

### Software Dependencies

- Python package manager (pip)
- Git for version control
- Docker (optional, for containerized deployment)
- MongoDB Compass (optional, for database management)

### API Access Requirements

- Weather API key (OpenWeatherMap or similar)
- Agricultural market data API access
- Satellite imagery API credentials
- Government schemes API access (if available)
- Pest management API credentials

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/agricultural-ai-system.git
cd agricultural-ai-system
```

### 2. Create Virtual Environment

```bash
python -m venv agricultural_ai_env
source agricultural_ai_env/bin/activate  # On Windows: agricultural_ai_env\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python -c "import asyncio, fastapi, motor, pandas, numpy; print('All dependencies installed successfully')"
```

## Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=agricultural_ai

# API Keys
WEATHER_API_KEY=your_openweathermap_api_key
MARKET_API_KEY=your_market_data_api_key
SATELLITE_API_KEY=your_satellite_api_key
PEST_API_KEY=your_pest_management_api_key
SCHEMES_API_KEY=your_government_schemes_api_key

# API Base URLs
WEATHER_API_BASE_URL=https://api.openweathermap.org/data/2.5
MARKET_API_BASE_URL=https://api.data.gov.in/resource
SATELLITE_API_BASE_URL=http://api.agromonitoring.com/agro/1.0
PEST_API_BASE_URL=https://api.pestnet.org/v1
SCHEMES_API_BASE_URL=https://api.gov.in/schemes

# System Configuration
DEBUG=true
LOG_LEVEL=INFO
MAX_WORKERS=5
CACHE_TTL_MINUTES=60

# Server Configuration
HOST=0.0.0.0
PORT=8000
RELOAD=false
```

### 2. Configuration File (Optional)

Create `config.json` for additional configuration:

```json
{
  "database": {
    "mongodb_uri": "mongodb://localhost:27017",
    "database_name": "agricultural_ai",
    "connection_timeout": 30
  },
  "apis": {
    "rate_limits": {
      "weather": 60,
      "market": 100,
      "satellite": 1000,
      "pest": 500,
      "schemes": 200
    },
    "timeout_seconds": 30
  },
  "system": {
    "debug_mode": true,
    "log_level": "INFO",
    "max_workers": 5,
    "cache_ttl_minutes": 60
  },
  "progressive_profiling": {
    "stages": {
      "registration": {
        "completion_threshold": 100,
        "follow_up_hours": 24
      },
      "basic_profiling": {
        "completion_threshold": 80,
        "follow_up_hours": 72
      }
    }
  }
}
```

## Database Setup

### 1. MongoDB Installation

**Ubuntu/Debian:**
```bash
wget -qO - https://www.mongodb.org/static/pgp/server-5.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/5.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-5.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod
```

**macOS:**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb/brew/mongodb-community
```

**Docker:**
```bash
docker run -d --name mongodb -p 27017:27017 -v mongodb_data:/data/db mongo:5.0
```

### 2. Database Initialization

Run the initialization script:

```bash
python -c "
import asyncio
from src.database.mongodb_setup import MongoDBSetup

async def init_db():
    db = MongoDBSetup()
    await db.connect()
    print('Database initialized successfully')
    await db.close_connection()

asyncio.run(init_db())
"
```

### 3. Create Sample Data (Optional)

```bash
python scripts/create_sample_data.py
```

### 4. Database Verification

```bash
mongosh
use agricultural_ai
show collections
db.farmer_profiles.countDocuments()
```

## API Configuration

### 1. Weather API Setup

Register at OpenWeatherMap:
1. Visit https://openweathermap.org/api
2. Sign up for a free account
3. Generate an API key
4. Add to `.env` file as `WEATHER_API_KEY`

### 2. Market Data API

For Indian market data:
1. Register at https://data.gov.in/
2. Subscribe to agricultural market data APIs
3. Add credentials to `.env` file

### 3. Satellite Imagery

For satellite data access:
1. Register with AgroMonitoring or similar service
2. Obtain API credentials
3. Configure in environment variables

### 4. API Testing

Test API connectivity:

```bash
python -c "
import asyncio
from src.apis.realtime_fetchers import RealTimeDataFetcher

async def test_apis():
    fetcher = RealTimeDataFetcher()
    location = {'latitude': 28.6139, 'longitude': 77.2090}
    
    try:
        result = await fetcher.fetch_all_data(location)
        print(f'API test successful: {result[\"fetch_summary\"][\"successful_fetches\"]} APIs working')
    except Exception as e:
        print(f'API test failed: {e}')

asyncio.run(test_apis())
"
```

## Deployment

### 1. Production Environment Setup

Create production environment file `.env.prod`:

```bash
# Production Database
MONGODB_URI=mongodb://username:password@prod-mongodb:27017/agricultural_ai?authSource=admin

# Production APIs (with production keys)
WEATHER_API_KEY=prod_weather_api_key
MARKET_API_KEY=prod_market_api_key

# Production System Settings
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
```

### 2. Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY .env .

EXPOSE 8000

CMD ["python", "src/main.py"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URI=mongodb://mongodb:27017/agricultural_ai
    depends_on:
      - mongodb
    volumes:
      - ./logs:/app/logs

  mongodb:
    image: mongo:5.0
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    environment:
      - MONGO_INITDB_DATABASE=agricultural_ai

volumes:
  mongodb_data:
```

Deploy with Docker Compose:

```bash
docker-compose up -d
```

### 3. Server Deployment

Using systemd service:

Create `/etc/systemd/system/agricultural-ai.service`:

```ini
[Unit]
Description=Agricultural AI System
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/agricultural-ai-system
Environment=PATH=/path/to/agricultural-ai-system/agricultural_ai_env/bin
ExecStart=/path/to/agricultural-ai-system/agricultural_ai_env/bin/python src/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Start the service:

```bash
sudo systemctl enable agricultural-ai
sudo systemctl start agricultural-ai
sudo systemctl status agricultural-ai
```

### 4. Nginx Configuration (Optional)

For production with Nginx reverse proxy:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Testing

### 1. Unit Tests

Run the complete test suite:

```bash
python -m pytest tests/ -v
```

Run specific test categories:

```bash
# Database tests
python -m pytest tests/test_agricultural_ai.py::TestMongoDBSetup -v

# API tests
python -m pytest tests/test_agricultural_ai.py::TestRealTimeDataFetchers -v

# Integration tests
python -m pytest tests/test_agricultural_ai.py::TestSystemIntegration -v
```

### 2. Load Testing

For performance testing:

```bash
pip install locust

# Create locustfile.py for load testing
locust -f tests/locustfile.py --host=http://localhost:8000
```

### 3. API Testing

Test API endpoints:

```bash
# Health check
curl http://localhost:8000/health

# System status
curl http://localhost:8000/api/system/status

# Farmer data (replace with actual farmer ID)
curl "http://localhost:8000/api/farmers/FARM001/comprehensive-data?latitude=28.6139&longitude=77.2090"
```

### 4. Database Testing

Verify database functionality:

```bash
python -c "
import asyncio
from src.database.mongodb_setup import MongoDBSetup

async def test_db():
    db = MongoDBSetup()
    await db.connect()
    
    # Test farmer profile creation
    profile_data = {
        'farmer_id': 'TEST001',
        'farmer_name': 'Test Farmer',
        'phone_number': '9876543210',
        'location': {
            'district': 'Test District',
            'state': 'Test State',
            'country': 'India',
            'coordinates': {'latitude': 28.6139, 'longitude': 77.2090}
        },
        'data_consent': True
    }
    
    result = await db.insert_farmer_profile(profile_data)
    print(f'Test profile created: {result}')
    
    retrieved = await db.get_farmer_profile('TEST001')
    print(f'Profile retrieved: {retrieved is not None}')
    
    await db.close_connection()

asyncio.run(test_db())
"
```

## Monitoring

### 1. Application Monitoring

Monitor system performance:

```bash
# Check system status
curl http://localhost:8000/api/system/status | python -m json.tool

# Monitor data collection jobs
curl http://localhost:8000/api/data-collection/jobs | python -m json.tool
```

### 2. Database Monitoring

Monitor MongoDB:

```bash
# Connect to MongoDB and check stats
mongosh
use agricultural_ai
db.stats()
db.farmer_profiles.countDocuments()
```

### 3. Log Monitoring

Monitor application logs:

```bash
tail -f agricultural_ai.log
```

Set up log rotation in `/etc/logrotate.d/agricultural-ai`:

```
/path/to/agricultural-ai-system/agricultural_ai.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
```

### 4. Performance Metrics

Key metrics to monitor:
- **API Response Times**: Average response time for different endpoints
- **Database Performance**: Query execution times and connection pool usage
- **Data Collection Success Rate**: Percentage of successful automated data collections
- **Profile Completion Rate**: Progressive profiling completion statistics
- **System Resource Usage**: CPU, memory, and disk utilization

### 5. Alerting Setup

Create monitoring script `monitor.py`:

```python
import asyncio
import aiohttp
from datetime import datetime

async def check_system_health():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('http://localhost:8000/health') as response:
                if response.status != 200:
                    print(f"ALERT: Health check failed with status {response.status}")
                    return False
                
                data = await response.json()
                if data['status'] != 'healthy':
                    print(f"ALERT: System status is {data['status']}")
                    return False
                
                print(f"System healthy at {datetime.now()}")
                return True
                
        except Exception as e:
            print(f"ALERT: Health check failed with error: {e}")
            return False

if __name__ == "__main__":
    asyncio.run(check_system_health())
```

Add to crontab for regular monitoring:

```bash
# Check every 5 minutes
*/5 * * * * cd /path/to/agricultural-ai-system && python monitor.py >> monitoring.log 2>&1
```

## Maintenance

### 1. Regular Updates

Update Python dependencies:

```bash
pip list --outdated
pip install --upgrade package_name
pip freeze > requirements.txt
```

Update system packages:

```bash
sudo apt update && sudo apt upgrade
```

### 2. Database Maintenance

Regular database maintenance tasks:

```javascript
// Connect to MongoDB
use agricultural_ai

// Rebuild indexes
db.farmer_profiles.reIndex()
db.farm_details.reIndex()

// Check database size
db.stats()

// Compact collections if needed
db.runCommand({compact: "farmer_profiles"})
```

### 3. Backup Procedures

Daily database backup:

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
mongodump --db agricultural_ai --out /backup/mongodb_$DATE
tar -czf /backup/mongodb_$DATE.tar.gz /backup/mongodb_$DATE
rm -rf /backup/mongodb_$DATE

# Keep only last 7 days of backups
find /backup -name "mongodb_*.tar.gz" -mtime +7 -delete
```

Add to crontab:

```bash
0 2 * * * /path/to/backup.sh >> /var/log/mongodb_backup.log 2>&1
```

### 4. Security Updates

Regular security maintenance:
- Update all dependencies to latest versions
- Review API keys and rotate regularly
- Monitor for security vulnerabilities
- Update database authentication credentials
- Review and update firewall rules

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues

**Problem**: `pymongo.errors.ServerSelectionTimeoutError`

**Solutions**:
```bash
# Check MongoDB status
sudo systemctl status mongod

# Check MongoDB logs
sudo tail -f /var/log/mongodb/mongod.log

# Verify connection string
python -c "from pymongo import MongoClient; client = MongoClient('mongodb://localhost:27017'); print(client.admin.command('ping'))"
```

#### 2. API Key Issues

**Problem**: API calls failing with authentication errors

**Solutions**:
```bash
# Verify API keys are set
echo $WEATHER_API_KEY

# Test API key directly
curl "https://api.openweathermap.org/data/2.5/weather?q=Delhi&appid=$WEATHER_API_KEY"

# Check API quotas and limits
```

#### 3. Memory Issues

**Problem**: System running out of memory

**Solutions**:
```bash
# Check memory usage
free -h
htop

# Optimize MongoDB memory usage
# Add to /etc/mongod.conf:
# storage:
#   wiredTiger:
#     engineConfig:
#       cacheSizeGB: 1

# Restart MongoDB
sudo systemctl restart mongod
```

#### 4. Performance Issues

**Problem**: Slow API responses

**Solutions**:
```bash
# Check database query performance
# In MongoDB shell:
db.setProfilingLevel(2, {slowms: 100})
db.system.profile.find().sort({ts: -1}).limit(5)

# Optimize database indexes
db.farmer_profiles.createIndex({"location.coordinates": "2dsphere"})
db.crop_history.createIndex({"farmer_id": 1, "crop_season": 1})

# Monitor API response times
curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8000/health
```

#### 5. Data Collection Issues

**Problem**: Automated data collection failing

**Solutions**:
```bash
# Check data collection status
curl http://localhost:8000/api/data-collection/jobs

# Manual trigger for testing
curl -X POST http://localhost:8000/api/data-collection/jobs/weather_realtime/trigger

# Check system logs for errors
tail -f agricultural_ai.log | grep -i error
```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# Set in .env file
DEBUG=true
LOG_LEVEL=DEBUG

# Restart application
sudo systemctl restart agricultural-ai
```

### Support and Documentation

- **System Logs**: Check `agricultural_ai.log` for detailed error information
- **API Documentation**: Visit `http://localhost:8000/docs` for interactive API documentation
- **Database Admin**: Use MongoDB Compass for visual database management
- **Performance Monitoring**: Implement monitoring dashboards using Grafana or similar tools

### Getting Help

If you encounter issues not covered in this guide:

1. Check the application logs for detailed error messages
2. Verify all configuration settings and API keys
3. Test individual components separately
4. Consult the API documentation at `/docs` endpoint
5. Review the test suite for example usage patterns

This implementation guide should help you successfully deploy and maintain the Agricultural AI System. Remember to regularly update dependencies and monitor system performance for optimal operation.