# Test Suite for Agricultural AI System

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import modules to test
from src.database.mongodb_setup import MongoDBSetup, validate_farmer_data
from src.apis.realtime_fetchers import WeatherAPIFetcher, APIConfig
from src.hybrid.managers import SoilHealthManager, RainfallPatternManager
from src.core.data_coordinator import DataCoordinator, DataRequest, DataCategory, DataPriority
from src.profiling.progressive_workflow import ProgressiveWorkflowManager, ProfileProgress
from src.automated.data_collector import AutomatedDataCollector, CollectionJob
from agricultural_ai_system.main import AgriculturalAISystem
from src.automated.data_collector import DataSourceType
# Test fixtures and utilities
@pytest.fixture
def sample_farmer_data():
    """Sample farmer data for testing"""
    return {
        "farmer_id": "TEST001",
        "farmer_name": "Test Farmer",
        "phone_number": "9876543210",
        "email": "test@example.com",
        "location": {
            "village": "Test Village",
            "district": "Test District",
            "state": "Test State",
            "country": "India",
            "coordinates": {
                "latitude": 28.6139,
                "longitude": 77.2090
            }
        },
        "experience_years": 10,
        "data_consent": True
    }

@pytest.fixture
def sample_location():
    """Sample location for testing"""
    return {"latitude": 28.6139, "longitude": 77.2090}

@pytest.fixture
def api_config():
    """Sample API configuration"""
    return APIConfig(
        base_url="https://api.test.com",
        api_key="test_key",
        rate_limit=60
    )

# Database Tests
class TestMongoDBSetup:
    """Test MongoDB setup and operations"""
    
    @pytest.mark.asyncio
    async def test_connection_initialization(self):
        """Test MongoDB connection initialization"""
        db_setup = MongoDBSetup(uri="mongodb://localhost:27017", db_name="test_db")
        
        # Mock the connection
        with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client:
            mock_client.return_value.admin.command = AsyncMock(return_value={"ok": 1})
            
            await db_setup.connect()
            assert db_setup.client is not None
            assert db_setup.db is not None
    
    @pytest.mark.asyncio
    async def test_farmer_profile_insertion(self, sample_farmer_data):
        """Test farmer profile insertion"""
        db_setup = MongoDBSetup()
        
        with patch.object(db_setup, 'collections') as mock_collections:
            mock_collections.__getitem__.return_value.insert_one = AsyncMock(
                return_value=Mock(inserted_id="test_id")
            )
            
            result = await db_setup.insert_farmer_profile(sample_farmer_data)
            assert result == "test_id"
    
    def test_farmer_data_validation(self, sample_farmer_data):
        """Test farmer data validation"""
        # Valid data should pass
        errors = validate_farmer_data(sample_farmer_data)
        assert len(errors) == 0
        
        # Invalid data should fail
        invalid_data = sample_farmer_data.copy()
        del invalid_data["farmer_name"]
        invalid_data["phone_number"] = "123"  # Too short
        
        errors = validate_farmer_data(invalid_data)
        assert len(errors) > 0
        assert any("farmer_name" in error for error in errors)
        assert any("phone number" in error for error in errors)

# API Fetchers Tests
class TestRealTimeDataFetchers:
    """Test real-time data fetchers"""
    
    @pytest.mark.asyncio
    async def test_weather_api_fetcher(self, api_config, sample_location):
        """Test weather API fetcher"""
        fetcher = WeatherAPIFetcher(api_config)
        
        # Mock response data
        mock_weather_data = {
            "name": "Test City",
            "main": {
                "temp": 25.0,
                "feels_like": 26.0,
                "humidity": 60,
                "pressure": 1013
            },
            "weather": [{"main": "Clear", "description": "clear sky"}],
            "wind": {"speed": 3.5, "deg": 180},
            "clouds": {"all": 10},
            "sys": {"sunrise": 1640835600, "sunset": 1640871000},
            "dt": 1640850000
        }
        
        with patch.object(fetcher, '_make_request', return_value=mock_weather_data):
            async with fetcher:
                result = await fetcher.fetch_current_weather(
                    sample_location["latitude"], 
                    sample_location["longitude"]
                )
                
                assert result["current_conditions"]["temperature"] == 25.0
                assert result["location"]["latitude"] == sample_location["latitude"]
                assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, api_config):
        """Test API rate limiting"""
        fetcher = WeatherAPIFetcher(api_config)
        fetcher.config.rate_limit = 2  # Set low limit for testing
        
        # Mock time to simulate rapid requests
        with patch('time.time') as mock_time:
            mock_time.return_value = 1640850000  # Fixed timestamp
            
            # First two requests should pass
            await fetcher._rate_limit_check()
            await fetcher._rate_limit_check()
            
            assert fetcher.request_count == 2
            
            # Third request should trigger rate limiting
            with patch('asyncio.sleep') as mock_sleep:
                await fetcher._rate_limit_check()
                mock_sleep.assert_called()

# Hybrid Managers Tests
class TestHybridManagers:
    """Test hybrid data managers"""
    
    @pytest.mark.asyncio
    async def test_soil_health_manager(self, sample_location):
        """Test soil health analysis"""
        manager = SoilHealthManager()
        
        # Sample soil data
        soil_data = [{
            "timestamp": datetime.now().isoformat(),
            "location": sample_location,
            "soil_moisture": 30.0,
            "soil_temperature": 22.0,
            "ph_level": 6.8,
            "nitrogen": 45.0,
            "phosphorus": 25.0,
            "potassium": 120.0,
            "organic_matter": 3.0,
            "electrical_conductivity": 1.2,
            "bulk_density": 1.35
        }]
        
        await manager.add_soil_data(soil_data)
        assert len(manager.soil_data) == 1
        
        # Test soil health calculation
        soil_health = await manager.calculate_soil_health_index(sample_location)
        assert soil_health.overall_score > 0
        assert soil_health.moisture_status is not None
    
    def test_soil_data_validation(self):
        """Test soil data validation"""
        manager = SoilHealthManager()
        
        # Create test soil data point
        from src.hybrid.managers import SoilDataPoint
        
        valid_point = SoilDataPoint(
            timestamp=datetime.now(),
            location={"latitude": 28.6139, "longitude": 77.2090},
            soil_moisture=30.0,
            soil_temperature=22.0,
            ph_level=6.8,
            nitrogen=45.0,
            phosphorus=25.0,
            potassium=120.0,
            organic_matter=3.0,
            electrical_conductivity=1.2,
            bulk_density=1.35
        )
        
        # Valid data should pass
        result = asyncio.run(manager._validate_soil_data(valid_point))
        assert result is True
        
        # Invalid data should fail
        invalid_point = valid_point
        invalid_point.soil_moisture = 150.0  # Invalid percentage
        
        result = asyncio.run(manager._validate_soil_data(invalid_point))
        assert result is False

# Data Coordinator Tests
class TestDataCoordinator:
    """Test data coordinator"""
    
    @pytest.mark.asyncio
    async def test_data_request_processing(self, sample_location):
        """Test data request processing"""
        coordinator = DataCoordinator()
        
        # Mock dependencies
        coordinator.db_manager = AsyncMock()
        coordinator.realtime_fetcher = AsyncMock()
        coordinator.hybrid_manager = AsyncMock()
        coordinator.is_initialized = True
        
        # Create test request
        request = DataRequest(
            request_id="test_request",
            category=DataCategory.FARMER_STATIC,
            data_type="farmer_profile",
            location=sample_location,
            farmer_id="TEST001"
        )
        
        # Mock farmer profile response
        coordinator.db_manager.get_farmer_profile.return_value = {"farmer_id": "TEST001"}
        
        response = await coordinator.process_data_request(request)
        
        assert response.request_id == "test_request"
        assert response.success is True
        assert response.data is not None
    
    def test_cache_functionality(self, sample_location):
        """Test caching functionality"""
        coordinator = DataCoordinator()
        
        request = DataRequest(
            request_id="cache_test",
            category=DataCategory.FARMER_STATIC,
            data_type="farmer_profile",
            location=sample_location,
            farmer_id="TEST001"
        )
        
        cache_key = coordinator._generate_cache_key(request)
        assert cache_key is not None
        assert isinstance(cache_key, str)
        
        # Test cache storage and retrieval
        test_data = {"test": "data"}
        coordinator._store_in_cache(cache_key, test_data, "farmer_profile")
        
        retrieved_data = coordinator._get_from_cache(cache_key)
        assert retrieved_data == test_data

# Progressive Workflow Tests
class TestProgressiveWorkflow:
    """Test progressive workflow manager"""
    
    def test_workflow_step_initialization(self):
        """Test workflow step initialization"""
        # Mock data coordinator
        mock_coordinator = Mock()
        manager = ProgressiveWorkflowManager(mock_coordinator)
        
        assert len(manager.workflow_definitions) > 0
        assert "basic_info" in manager.workflow_definitions
        
        # Test workflow step structure
        basic_info_step = manager.workflow_definitions["basic_info"]
        assert basic_info_step.step_name == "Basic Information"
        assert "farmer_name" in basic_info_step.required_fields
    
    @pytest.mark.asyncio
    async def test_farmer_profile_initialization(self, sample_farmer_data):
        """Test farmer profile initialization"""
        mock_coordinator = Mock()
        manager = ProgressiveWorkflowManager(mock_coordinator)
        
        progress = await manager.initialize_farmer_profile("TEST001", sample_farmer_data)
        
        assert progress.farmer_id == "TEST001"
        assert progress.completion_percentage > 0
        assert len(progress.pending_actions) > 0
    
    def test_step_data_validation(self):
        """Test workflow step data validation"""
        mock_coordinator = Mock()
        manager = ProgressiveWorkflowManager(mock_coordinator)
        
        basic_info_step = manager.workflow_definitions["basic_info"]
        
        # Valid data
        valid_data = {
            "farmer_name": "Test Farmer",
            "phone_number": "9876543210",
            "village": "Test Village",
            "district": "Test District",
            "state": "Test State"
        }
        
        validation = manager._validate_step_data(basic_info_step, valid_data)
        assert validation["is_valid"] is True
        
        # Invalid data (missing required field)
        invalid_data = valid_data.copy()
        del invalid_data["farmer_name"]
        
        validation = manager._validate_step_data(basic_info_step, invalid_data)
        assert validation["is_valid"] is False
        assert "farmer_name" in validation["missing_fields"]

# Data Collector Tests
class TestDataCollector:
    """Test automated data collector"""
    
    def test_collection_job_creation(self):
        """Test collection job creation"""
        from src.automated.data_collector import CollectionFrequency, DataSourceType
        
        job = CollectionJob(
            job_id="test_job",
            job_name="Test Collection Job",
            data_type="weather_data",
            category=DataCategory.REALTIME_EXTERNAL,
            frequency=CollectionFrequency.HOURLY,
            source_type=DataSourceType.API_ENDPOINT
        )
        
        assert job.job_id == "test_job"
        assert job.is_active is True
        assert job.success_count == 0
    
    @pytest.mark.asyncio
    async def test_data_collector_initialization(self):
        """Test data collector initialization"""
        mock_coordinator = AsyncMock()
        mock_workflow = Mock()
        
        collector = AutomatedDataCollector(mock_coordinator, mock_workflow)
        
        assert len(collector.collection_jobs) > 0
        assert "weather_realtime" in collector.collection_jobs
        assert collector.is_running is False
    
    def test_next_run_time_calculation(self):
        """Test next run time calculation"""
        mock_coordinator = AsyncMock()
        mock_workflow = Mock()
        collector = AutomatedDataCollector(mock_coordinator, mock_workflow)
        
        from src.automated.data_collector import CollectionFrequency
        
        # Create test job
        job = CollectionJob(
            job_id="test_hourly",
            job_name="Test Hourly Job",
            data_type="test_data",
            category=DataCategory.REALTIME_EXTERNAL,
            frequency=CollectionFrequency.HOURLY,
            source_type=DataSourceType.API_ENDPOINT
        )
        
        next_run = collector._calculate_next_run_time(job)
        now = datetime.utcnow()
        
        # Should be approximately 1 hour from now
        time_diff = (next_run - now).total_seconds()
        assert 3500 <= time_diff <= 3700  # Allow some tolerance

# Integration Tests
class TestSystemIntegration:
    """Test system integration"""
    
    @pytest.mark.asyncio
    async def test_system_initialization(self):
        """Test complete system initialization"""
        # Mock database connection
        with patch('motor.motor_asyncio.AsyncIOMotorClient'):
            system = AgriculturalAISystem()
            
            # Mock all async operations
            with patch.object(system, '_load_configuration', return_value={
                "database": {"mongodb_uri": "mongodb://test", "database_name": "test"},
                "apis": {},
                "system": {"debug_mode": True},
                "server": {"host": "0.0.0.0", "port": 8000}
            }):
                # System should initialize without errors
                assert system.config is not None
                assert system.app is not None
    
    def test_configuration_loading(self):
        """Test configuration loading"""
        system = AgriculturalAISystem()
        config = system._load_configuration()
        
        assert "database" in config
        assert "apis" in config
        assert "system" in config
        assert "server" in config
    
    @pytest.mark.asyncio
    async def test_fastapi_health_endpoint(self):
        """Test FastAPI health endpoint"""
        system = AgriculturalAISystem()
        
        # Import test client
        from fastapi.testclient import TestClient
        client = TestClient(system.app)
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data

# Performance Tests
class TestPerformance:
    """Test system performance"""
    
    @pytest.mark.asyncio
    async def test_concurrent_data_requests(self):
        """Test handling multiple concurrent data requests"""
        coordinator = DataCoordinator()
        coordinator.is_initialized = True
        
        # Mock successful responses
        with patch.object(coordinator, '_process_farmer_static_request', 
                         return_value={"test": "data"}):
            
            # Create multiple requests
            requests = []
            for i in range(10):
                request = DataRequest(
                    request_id=f"perf_test_{i}",
                    category=DataCategory.FARMER_STATIC,
                    data_type="farmer_profile",
                    location={"latitude": 28.6139, "longitude": 77.2090},
                    farmer_id=f"FARM{i:03d}"
                )
                requests.append(coordinator.process_data_request(request))
            
            # Execute all requests concurrently
            start_time = datetime.utcnow()
            responses = await asyncio.gather(*requests)
            end_time = datetime.utcnow()
            
            # All requests should succeed
            assert len(responses) == 10
            assert all(response.success for response in responses)
            
            # Should complete reasonably quickly
            total_time = (end_time - start_time).total_seconds()
            assert total_time < 5.0  # Should complete within 5 seconds
    
    def test_memory_usage_data_structures(self):
        """Test memory efficiency of data structures"""
        import sys
        
        # Test farmer data storage efficiency
        farmer_data = {
            "farmer_id": "TEST001",
            "farmer_name": "Test Farmer" * 100,  # Large name
            "location": {"latitude": 28.6139, "longitude": 77.2090},
            "additional_data": ["data"] * 1000  # Large data array
        }
        
        size = sys.getsizeof(farmer_data)
        
        # Should be reasonable size (less than 100KB for this test data)
        assert size < 100000

# Error Handling Tests
class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test handling of database connection failures"""
        db_setup = MongoDBSetup(uri="mongodb://invalid:27017")
        
        # Should raise exception on connection failure
        with pytest.raises(Exception):
            await db_setup.connect()
    
    @pytest.mark.asyncio
    async def test_api_failure_handling(self, api_config):
        """Test API failure handling"""
        fetcher = WeatherAPIFetcher(api_config)
        
        # Mock network error
        with patch.object(fetcher, '_make_request', side_effect=Exception("Network error")):
            async with fetcher:
                with pytest.raises(Exception):
                    await fetcher.fetch_current_weather(28.6139, 77.2090)
    
    @pytest.mark.asyncio
    async def test_invalid_data_handling(self):
        """Test handling of invalid data"""
        coordinator = DataCoordinator()
        coordinator.is_initialized = True
        
        # Invalid request with missing required fields
        request = DataRequest(
            request_id="invalid_test",
            category=DataCategory.FARMER_STATIC,
            data_type="farmer_profile",
            location={},  # Empty location
            farmer_id=""  # Empty farmer ID
        )
        
        response = await coordinator.process_data_request(request)
        
        # Should handle gracefully and return error
        assert response.success is False
        assert response.error is not None

# Load and Stress Tests
@pytest.mark.slow
class TestLoadAndStress:
    """Load and stress tests (marked as slow)"""
    
    @pytest.mark.asyncio
    async def test_high_volume_data_processing(self):
        """Test processing high volumes of data"""
        manager = SoilHealthManager()
        
        # Generate large dataset
        soil_data = []
        for i in range(1000):
            soil_data.append({
                "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
                "location": {"latitude": 28.6139, "longitude": 77.2090},
                "soil_moisture": 25.0 + (i % 20),
                "soil_temperature": 20.0 + (i % 10),
                "ph_level": 6.5 + (i % 3) * 0.1,
                "nitrogen": 40.0 + (i % 30),
                "phosphorus": 20.0 + (i % 20),
                "potassium": 100.0 + (i % 50),
                "organic_matter": 2.5 + (i % 5) * 0.1,
                "electrical_conductivity": 1.0 + (i % 10) * 0.1,
                "bulk_density": 1.3 + (i % 5) * 0.05
            })
        
        start_time = datetime.utcnow()
        await manager.add_soil_data(soil_data)
        end_time = datetime.utcnow()
        
        processing_time = (end_time - start_time).total_seconds()
        
        assert len(manager.soil_data) == 1000
        assert processing_time < 10.0  # Should process 1000 records in under 10 seconds

# Utility functions for tests
def create_test_database():
    """Create test database for integration tests"""
    # This would set up a test MongoDB instance
    pass

def cleanup_test_data():
    """Clean up test data after tests"""
    # This would clean up any test data created
    pass

# Test configuration
pytest_plugins = ["pytest_asyncio"]

# Custom markers
pytestmark = pytest.mark.asyncio

# Test suite summary
if __name__ == "__main__":
    """Run specific tests or all tests"""
    import pytest
    
    # Run all tests
    pytest.main(["-v", __file__])