# STEP 4: Data Coordinator to Integrate All Categories

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
import json
import uuid
from enum import Enum
from src.database.mongodb_setup import MongoDBSetup

from src.apis.realtime_fetchers import RealTimeDataFetcher
from src.hybrid.managers import HybridDataManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCategory(Enum):
    """Data categories for agricultural AI system"""
    FARMER_STATIC = "farmer_static"      # Category 1: Farmer profiles, static data
    REALTIME_EXTERNAL = "realtime_external"  # Category 2: Weather, market, satellite, etc.
    HYBRID_COMPUTED = "hybrid_computed"   # Category 3: Soil health, rainfall patterns

class DataPriority(Enum):
    """Data priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class DataRequest:
    """Data request structure"""
    request_id: str
    category: DataCategory
    data_type: str
    location: Dict[str, float]
    farmer_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: DataPriority = DataPriority.MEDIUM
    requested_at: datetime = field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None

@dataclass
class DataResponse:
    """Data response structure"""
    request_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    data_sources: List[str] = field(default_factory=list)
    quality_score: float = 1.0
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    cache_info: Dict[str, Any] = field(default_factory=dict)

class DataCoordinator:
    """
    Central coordinator for all agricultural AI system data
    Integrates farmer static data, real-time external data, and hybrid computed data
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize data coordinator
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Initialize data managers
        self.db_manager = MongoDBSetup()
        self.realtime_fetcher = RealTimeDataFetcher()
        self.hybrid_manager = HybridDataManager()
        
        # Request tracking
        self.active_requests: Dict[str, DataRequest] = {}
        self.request_history: List[DataRequest] = []
        
        # Caching system
        self.cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}
        
        # Performance metrics
        self.performance_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize all data managers and connections"""
        try:
            logger.info("Initializing Data Coordinator...")
            
            # Initialize database connection
            await self.db_manager.connect()
            logger.info("Database manager initialized")
            
            # Real-time fetcher is initialized on-demand
            logger.info("Real-time fetcher ready")
            
            # Hybrid manager is ready
            logger.info("Hybrid data manager ready")
            
            self.is_initialized = True
            logger.info("Data Coordinator initialization completed")
            
        except Exception as e:
            logger.error(f"Error initializing Data Coordinator: {e}")
            raise
    
    async def process_data_request(self, request: DataRequest) -> DataResponse:
        """
        Process a data request by routing to appropriate managers
        
        Args:
            request: Data request object
            
        Returns:
            Data response object
        """
        if not self.is_initialized:
            await self.initialize()
        
        start_time = datetime.utcnow()
        self.performance_metrics["total_requests"] += 1
        
        try:
            # Track request
            self.active_requests[request.request_id] = request
            logger.info(f"Processing request {request.request_id} for {request.data_type}")
            
            # Check cache first
            cache_key = self._generate_cache_key(request)
            cached_data = self._get_from_cache(cache_key)
            
            if cached_data:
                self.performance_metrics["cache_hits"] += 1
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                
                return DataResponse(
                    request_id=request.request_id,
                    success=True,
                    data=cached_data,
                    data_sources=["cache"],
                    processing_time=processing_time,
                    cache_info={"cache_hit": True, "cached_at": self.cache_ttl[cache_key]}
                )
            
            self.performance_metrics["cache_misses"] += 1
            
            # Route request to appropriate manager
            if request.category == DataCategory.FARMER_STATIC:
                response_data = await self._process_farmer_static_request(request)
            elif request.category == DataCategory.REALTIME_EXTERNAL:
                response_data = await self._process_realtime_request(request)
            elif request.category == DataCategory.HYBRID_COMPUTED:
                response_data = await self._process_hybrid_request(request)
            else:
                raise ValueError(f"Unknown data category: {request.category}")
            
            # Cache the result
            if response_data:
                self._store_in_cache(cache_key, response_data, request.data_type)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Create response
            response = DataResponse(
                request_id=request.request_id,
                success=True,
                data=response_data,
                data_sources=self._get_data_sources(request.data_type),
                quality_score=self._calculate_quality_score(response_data),
                processing_time=processing_time,
                cache_info={"cache_hit": False}
            )
            
            self.performance_metrics["successful_requests"] += 1
            logger.info(f"Successfully processed request {request.request_id} in {processing_time:.2f}s")
            
            return response
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.performance_metrics["failed_requests"] += 1
            
            error_response = DataResponse(
                request_id=request.request_id,
                success=False,
                error=str(e),
                processing_time=processing_time
            )
            
            logger.error(f"Failed to process request {request.request_id}: {e}")
            return error_response
            
        finally:
            # Clean up
            if request.request_id in self.active_requests:
                self.request_history.append(self.active_requests.pop(request.request_id))
            
            # Update average response time
            self._update_performance_metrics()
    
    async def _process_farmer_static_request(self, request: DataRequest) -> Dict[str, Any]:
        """Process farmer static data requests"""
        try:
            if request.data_type == "farmer_profile":
                if not request.farmer_id:
                    raise ValueError("farmer_id required for farmer_profile request")
                
                profile = await self.db_manager.get_farmer_profile(request.farmer_id)
                return {"farmer_profile": profile}
            
            elif request.data_type == "farm_details":
                if not request.farmer_id:
                    raise ValueError("farmer_id required for farm_details request")
                
                # Get farms by farmer ID (implementation depends on your schema)
                farms = await self._get_farms_by_farmer_id(request.farmer_id)
                return {"farm_details": farms}
            
            elif request.data_type == "crop_history":
                if not request.farmer_id:
                    raise ValueError("farmer_id required for crop_history request")
                
                crop_history = await self._get_crop_history(request.farmer_id, request.parameters)
                return {"crop_history": crop_history}
            
            elif request.data_type == "regional_farmers":
                district = request.parameters.get("district")
                state = request.parameters.get("state")
                
                if not district:
                    raise ValueError("district parameter required for regional_farmers request")
                
                farmers = await self.db_manager.get_farms_by_location(district, state)
                return {"regional_farmers": farmers}
            
            elif request.data_type == "crop_statistics":
                crop_type = request.parameters.get("crop_type", "wheat")
                season = request.parameters.get("season")
                
                stats = await self.db_manager.get_crop_statistics(crop_type, season)
                return {"crop_statistics": stats}
            
            else:
                raise ValueError(f"Unknown farmer static data type: {request.data_type}")
                
        except Exception as e:
            logger.error(f"Error processing farmer static request: {e}")
            raise
    
    async def _process_realtime_request(self, request: DataRequest) -> Dict[str, Any]:
        """Process real-time external data requests"""
        try:
            location = request.location
            parameters = request.parameters
            
            if request.data_type == "current_weather":
                # Fetch current weather data
                results = await self.realtime_fetcher.fetch_all_data(
                    location=location,
                    **parameters
                )
                return {"weather_data": results["data"]["weather"]}
            
            elif request.data_type == "market_prices":
                commodity = parameters.get("commodity", "wheat")
                state = parameters.get("state")
                
                results = await self.realtime_fetcher.fetch_all_data(
                    location=location,
                    commodity=commodity,
                    state=state
                )
                return {"market_data": results["data"]["market"]}
            
            elif request.data_type == "satellite_imagery":
                start_date = parameters.get("start_date")
                end_date = parameters.get("end_date")
                
                results = await self.realtime_fetcher.fetch_all_data(
                    location=location,
                    start_date=start_date,
                    end_date=end_date
                )
                return {"satellite_data": results["data"]["satellite"]}
            
            elif request.data_type == "pest_alerts":
                crop_type = parameters.get("crop_type", "wheat")
                region = parameters.get("region", "india")
                
                results = await self.realtime_fetcher.fetch_all_data(
                    location=location,
                    crop_type=crop_type,
                    region=region
                )
                return {"pest_data": results["data"]["pest"]}
            
            elif request.data_type == "government_schemes":
                state = parameters.get("state")
                category = parameters.get("category")
                
                results = await self.realtime_fetcher.fetch_all_data(
                    location=location,
                    state=state,
                    scheme_category=category
                )
                return {"schemes_data": results["data"]["schemes"]}
            
            elif request.data_type == "comprehensive_realtime":
                # Fetch all real-time data
                results = await self.realtime_fetcher.fetch_all_data(
                    location=location,
                    **parameters
                )
                return {"comprehensive_realtime": results}
            
            else:
                raise ValueError(f"Unknown real-time data type: {request.data_type}")
                
        except Exception as e:
            logger.error(f"Error processing real-time request: {e}")
            raise
    
    async def _process_hybrid_request(self, request: DataRequest) -> Dict[str, Any]:
        """Process hybrid computed data requests"""
        try:
            location = request.location
            parameters = request.parameters
            
            if request.data_type == "soil_health_analysis":
                # Get soil health data
                soil_health = await self.hybrid_manager.soil_manager.calculate_soil_health_index(
                    location=location,
                    time_window_days=parameters.get("time_window_days", 30)
                )
                return {"soil_health": soil_health.__dict__}
            
            elif request.data_type == "rainfall_pattern_analysis":
                # Get rainfall pattern analysis
                rainfall_patterns = await self.hybrid_manager.rainfall_manager.analyze_rainfall_patterns(
                    location=location,
                    analysis_days=parameters.get("analysis_days", 365)
                )
                return {"rainfall_patterns": rainfall_patterns}
            
            elif request.data_type == "integrated_analysis":
                # Get integrated soil and rainfall analysis
                # This requires sample data - in production, this would come from sensors/APIs
                soil_data = parameters.get("soil_data", [])
                rainfall_data = parameters.get("rainfall_data", [])
                
                if not soil_data or not rainfall_data:
                    # Generate sample data for demonstration
                    soil_data, rainfall_data = self._generate_sample_hybrid_data(location)
                
                integrated_results = await self.hybrid_manager.integrate_data(
                    soil_data=soil_data,
                    rainfall_data=rainfall_data
                )
                return {"integrated_analysis": integrated_results}
            
            elif request.data_type == "crop_recommendation":
                # Comprehensive crop recommendation based on all available data
                crop_recommendation = await self._generate_crop_recommendation(
                    location=location,
                    farmer_id=request.farmer_id,
                    parameters=parameters
                )
                return {"crop_recommendation": crop_recommendation}
            
            else:
                raise ValueError(f"Unknown hybrid data type: {request.data_type}")
                
        except Exception as e:
            logger.error(f"Error processing hybrid request: {e}")
            raise
    
    async def _generate_crop_recommendation(self, location: Dict[str, float], 
                                          farmer_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive crop recommendation"""
        try:
            recommendations = {
                "location": location,
                "farmer_id": farmer_id,
                "analysis_timestamp": datetime.utcnow(),
                "recommendations": []
            }
            
            # Get farmer profile for context
            if farmer_id:
                farmer_profile = await self.db_manager.get_farmer_profile(farmer_id)
                if farmer_profile:
                    recommendations["farmer_context"] = {
                        "experience_years": farmer_profile.get("experience_years", 0),
                        "farm_size": farmer_profile.get("farm_size", 0),
                        "previous_crops": farmer_profile.get("preferred_crops", [])
                    }
            
            # Get soil health analysis
            try:
                soil_health = await self.hybrid_manager.soil_manager.calculate_soil_health_index(location)
                recommendations["soil_suitability"] = {
                    "overall_score": soil_health.overall_score,
                    "limiting_factors": soil_health.risk_factors,
                    "improvements_needed": soil_health.recommendations
                }
            except Exception as e:
                logger.warning(f"Could not get soil health data: {e}")
            
            # Get weather patterns
            try:
                # Fetch current weather
                weather_request = DataRequest(
                    request_id=str(uuid.uuid4()),
                    category=DataCategory.REALTIME_EXTERNAL,
                    data_type="current_weather",
                    location=location
                )
                weather_response = await self._process_realtime_request(weather_request)
                recommendations["weather_context"] = weather_response.get("weather_data", {})
            except Exception as e:
                logger.warning(f"Could not get weather data: {e}")
            
            # Generate crop recommendations based on available data
            crop_suggestions = self._suggest_crops_based_on_conditions(
                location, recommendations.get("soil_suitability", {}),
                recommendations.get("weather_context", {}), parameters
            )
            
            recommendations["recommended_crops"] = crop_suggestions
            recommendations["general_advice"] = self._generate_general_farming_advice(recommendations)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating crop recommendation: {e}")
            raise
    
    def _suggest_crops_based_on_conditions(self, location: Dict[str, float],
                                         soil_data: Dict[str, Any],
                                         weather_data: Dict[str, Any],
                                         parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest crops based on soil and weather conditions"""
        
        # Basic crop database with suitability criteria
        crop_database = {
            "wheat": {
                "soil_ph_range": (6.0, 7.5),
                "temperature_range": (15, 25),
                "rainfall_requirement": (300, 750),
                "soil_type": ["loam", "clay_loam"],
                "season": "rabi"
            },
            "rice": {
                "soil_ph_range": (5.5, 7.0),
                "temperature_range": (20, 35),
                "rainfall_requirement": (1000, 2000),
                "soil_type": ["clay", "clay_loam"],
                "season": "kharif"
            },
            "maize": {
                "soil_ph_range": (6.0, 7.5),
                "temperature_range": (18, 30),
                "rainfall_requirement": (500, 1200),
                "soil_type": ["loam", "sandy_loam"],
                "season": "kharif"
            },
            "cotton": {
                "soil_ph_range": (5.8, 8.0),
                "temperature_range": (20, 35),
                "rainfall_requirement": (600, 1200),
                "soil_type": ["black_soil", "alluvial"],
                "season": "kharif"
            },
            "tomato": {
                "soil_ph_range": (6.0, 7.0),
                "temperature_range": (20, 30),
                "rainfall_requirement": (600, 1000),
                "soil_type": ["loam", "sandy_loam"],
                "season": "all_year"
            }
        }
        
        suggestions = []
        current_season = parameters.get("season", "kharif")
        
        for crop_name, criteria in crop_database.items():
            suitability_score = 0
            suitability_notes = []
            
            # Check season compatibility
            if criteria["season"] in [current_season, "all_year"]:
                suitability_score += 20
                suitability_notes.append("Season compatible")
            else:
                suitability_notes.append(f"Better for {criteria['season']} season")
            
            # Check soil pH if available
            if soil_data.get("overall_score", 0) > 70:
                suitability_score += 30
                suitability_notes.append("Soil conditions favorable")
            elif soil_data.get("overall_score", 0) > 40:
                suitability_score += 15
                suitability_notes.append("Soil conditions acceptable")
            else:
                suitability_notes.append("Soil improvement needed")
            
            # Check weather conditions if available
            if weather_data and weather_data.get("success"):
                current_temp = weather_data.get("data", {}).get("current_conditions", {}).get("temperature", 25)
                if criteria["temperature_range"][0] <= current_temp <= criteria["temperature_range"][1]:
                    suitability_score += 25
                    suitability_notes.append("Temperature suitable")
                else:
                    suitability_notes.append("Temperature may be challenging")
            
            # Location-based bonus (simplified)
            latitude = location.get("latitude", 0)
            if 20 <= latitude <= 35:  # Good agricultural zone for India
                suitability_score += 25
                suitability_notes.append("Geographic location suitable")
            
            # Create crop suggestion
            suggestion = {
                "crop_name": crop_name,
                "suitability_score": min(suitability_score, 100),
                "suitability_level": self._get_suitability_level(suitability_score),
                "notes": suitability_notes,
                "requirements": criteria,
                "estimated_yield": f"{criteria.get('yield_range', (2, 5))[0]}-{criteria.get('yield_range', (2, 5))[1]} tons/hectare"
            }
            
            suggestions.append(suggestion)
        
        # Sort by suitability score
        suggestions.sort(key=lambda x: x["suitability_score"], reverse=True)
        
        return suggestions[:5]  # Top 5 suggestions
    
    def _get_suitability_level(self, score: float) -> str:
        """Get suitability level based on score"""
        if score >= 80:
            return "Highly Suitable"
        elif score >= 60:
            return "Suitable"
        elif score >= 40:
            return "Moderately Suitable"
        else:
            return "Less Suitable"
    
    def _generate_general_farming_advice(self, recommendations: Dict[str, Any]) -> List[str]:
        """Generate general farming advice"""
        advice = []
        
        # Soil-based advice
        soil_data = recommendations.get("soil_suitability", {})
        if soil_data.get("overall_score", 0) < 50:
            advice.append("Focus on soil improvement through organic matter addition")
        
        # Weather-based advice
        weather_data = recommendations.get("weather_context", {})
        if weather_data and weather_data.get("success"):
            current_conditions = weather_data.get("data", {}).get("current_conditions", {})
            if current_conditions.get("humidity", 50) > 80:
                advice.append("Monitor for fungal diseases due to high humidity")
            if current_conditions.get("temperature", 25) > 35:
                advice.append("Ensure adequate irrigation during high temperature periods")
        
        # Seasonal advice
        current_month = datetime.now().month
        if current_month in [3, 4, 5]:  # Spring
            advice.append("Good time for summer crop preparation and soil treatment")
        elif current_month in [6, 7, 8]:  # Monsoon
            advice.append("Monitor water drainage and pest management during monsoon")
        
        return advice
    
    def _generate_sample_hybrid_data(self, location: Dict[str, float]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Generate sample data for demonstration purposes"""
        
        # Sample soil data
        soil_data = [{
            "timestamp": datetime.now().isoformat(),
            "location": location,
            "soil_moisture": 28.5,
            "soil_temperature": 22.0,
            "ph_level": 6.8,
            "nitrogen": 45.0,
            "phosphorus": 25.0,
            "potassium": 120.0,
            "organic_matter": 3.2,
            "electrical_conductivity": 1.1,
            "bulk_density": 1.32
        }]
        
        # Sample rainfall data
        rainfall_data = [{
            "timestamp": datetime.now().isoformat(),
            "location": location,
            "precipitation": 12.5,
            "intensity": 5.2,
            "duration": 90,
            "temperature": 24.0,
            "humidity": 78.0,
            "pressure": 1012.3
        }]
        
        return soil_data, rainfall_data
    
    async def _get_farms_by_farmer_id(self, farmer_id: str) -> List[Dict[str, Any]]:
        """Get farm details by farmer ID"""
        # This would be implemented based on your database schema
        # For now, return a placeholder
        return [{"message": f"Farm details for farmer {farmer_id} would be retrieved here"}]
    
    async def _get_crop_history(self, farmer_id: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get crop history for farmer"""
        # This would be implemented based on your database schema
        return [{"message": f"Crop history for farmer {farmer_id} would be retrieved here"}]
    
    def _generate_cache_key(self, request: DataRequest) -> str:
        """Generate cache key for request"""
        key_parts = [
            request.category.value,
            request.data_type,
            str(request.location.get("latitude", 0)),
            str(request.location.get("longitude", 0))
        ]
        
        if request.farmer_id:
            key_parts.append(request.farmer_id)
        
        # Add relevant parameters
        for key in sorted(request.parameters.keys()):
            key_parts.append(f"{key}:{request.parameters[key]}")
        
        return "|".join(key_parts)
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if valid"""
        if cache_key in self.cache:
            if cache_key in self.cache_ttl and datetime.utcnow() < self.cache_ttl[cache_key]:
                return self.cache[cache_key]
            else:
                # Remove expired cache
                if cache_key in self.cache:
                    del self.cache[cache_key]
                if cache_key in self.cache_ttl:
                    del self.cache_ttl[cache_key]
        
        return None
    
    def _store_in_cache(self, cache_key: str, data: Dict[str, Any], data_type: str):
        """Store data in cache with appropriate TTL"""
        # Set TTL based on data type
        ttl_minutes = {
            "farmer_profile": 60,           # 1 hour
            "current_weather": 10,          # 10 minutes
            "market_prices": 30,           # 30 minutes
            "satellite_imagery": 1440,     # 24 hours
            "soil_health_analysis": 720,   # 12 hours
            "rainfall_pattern_analysis": 1440  # 24 hours
        }
        
        ttl = ttl_minutes.get(data_type, 60)  # Default 1 hour
        self.cache[cache_key] = data
        self.cache_ttl[cache_key] = datetime.utcnow() + timedelta(minutes=ttl)
        
        # Clean up old cache entries (simple LRU)
        if len(self.cache) > 1000:  # Max cache size
            oldest_key = min(self.cache_ttl.keys(), key=lambda k: self.cache_ttl[k])
            del self.cache[oldest_key]
            del self.cache_ttl[oldest_key]
    
    def _get_data_sources(self, data_type: str) -> List[str]:
        """Get data sources for data type"""
        source_mapping = {
            "farmer_profile": ["mongodb"],
            "current_weather": ["openweathermap"],
            "market_prices": ["government_api"],
            "satellite_imagery": ["satellite_api"],
            "pest_alerts": ["pest_api"],
            "government_schemes": ["government_schemes_api"],
            "soil_health_analysis": ["sensor_data", "computed"],
            "rainfall_pattern_analysis": ["weather_stations", "computed"]
        }
        
        return source_mapping.get(data_type, ["unknown"])
    
    def _calculate_quality_score(self, data: Dict[str, Any]) -> float:
        """Calculate data quality score"""
        if not data:
            return 0.0
        
        # Simple quality scoring based on data completeness and freshness
        score = 1.0
        
        # Check for errors
        if "error" in data:
            score -= 0.3
        
        # Check data completeness (simplified)
        if isinstance(data, dict):
            if len(data) < 3:  # Very sparse data
                score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _update_performance_metrics(self):
        """Update performance metrics"""
        if self.performance_metrics["total_requests"] > 0:
            success_rate = (self.performance_metrics["successful_requests"] / 
                          self.performance_metrics["total_requests"])
            self.performance_metrics["success_rate"] = success_rate
            
            cache_hit_rate = (self.performance_metrics["cache_hits"] / 
                            (self.performance_metrics["cache_hits"] + self.performance_metrics["cache_misses"]))
            self.performance_metrics["cache_hit_rate"] = cache_hit_rate
    
    async def get_comprehensive_farmer_data(self, farmer_id: str, 
                                          location: Dict[str, float]) -> Dict[str, Any]:
        """
        Get comprehensive data for a farmer including all categories
        
        Args:
            farmer_id: Farmer identifier
            location: Farm location coordinates
            
        Returns:
            Comprehensive farmer data
        """
        try:
            # Create requests for all data types
            requests = [
                DataRequest(
                    request_id=str(uuid.uuid4()),
                    category=DataCategory.FARMER_STATIC,
                    data_type="farmer_profile",
                    location=location,
                    farmer_id=farmer_id,
                    priority=DataPriority.HIGH
                ),
                DataRequest(
                    request_id=str(uuid.uuid4()),
                    category=DataCategory.REALTIME_EXTERNAL,
                    data_type="comprehensive_realtime",
                    location=location,
                    farmer_id=farmer_id,
                    priority=DataPriority.HIGH
                ),
                DataRequest(
                    request_id=str(uuid.uuid4()),
                    category=DataCategory.HYBRID_COMPUTED,
                    data_type="crop_recommendation",
                    location=location,
                    farmer_id=farmer_id,
                    priority=DataPriority.HIGH
                )
            ]
            
            # Process all requests concurrently
            tasks = [self.process_data_request(req) for req in requests]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            comprehensive_data = {
                "farmer_id": farmer_id,
                "location": location,
                "data_timestamp": datetime.utcnow(),
                "farmer_static_data": None,
                "realtime_external_data": None,
                "hybrid_computed_data": None,
                "errors": []
            }
            
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    comprehensive_data["errors"].append(str(response))
                    continue
                
                if response.success:
                    if requests[i].category == DataCategory.FARMER_STATIC:
                        comprehensive_data["farmer_static_data"] = response.data
                    elif requests[i].category == DataCategory.REALTIME_EXTERNAL:
                        comprehensive_data["realtime_external_data"] = response.data
                    elif requests[i].category == DataCategory.HYBRID_COMPUTED:
                        comprehensive_data["hybrid_computed_data"] = response.data
                else:
                    comprehensive_data["errors"].append(response.error)
            
            logger.info(f"Compiled comprehensive data for farmer {farmer_id}")
            return comprehensive_data
            
        except Exception as e:
            logger.error(f"Error getting comprehensive farmer data: {e}")
            raise
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report for the data coordinator"""
        return {
            "performance_metrics": self.performance_metrics,
            "cache_statistics": {
                "cache_size": len(self.cache),
                "active_cache_entries": len([k for k, v in self.cache_ttl.items() if v > datetime.utcnow()])
            },
            "active_requests": len(self.active_requests),
            "request_history_size": len(self.request_history),
            "report_timestamp": datetime.utcnow()
        }
    
    async def cleanup_resources(self):
        """Clean up resources and close connections"""
        try:
            await self.db_manager.close_connection()
            
            # Clear caches
            self.cache.clear()
            self.cache_ttl.clear()
            
            logger.info("Data Coordinator resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up resources: {e}")

# Example usage
async def main():
    """Example usage of DataCoordinator"""
    
    coordinator = DataCoordinator()
    
    try:
        # Initialize
        await coordinator.initialize()
        
        # Example location (Delhi, India)
        location = {"latitude": 28.6139, "longitude": 77.2090}
        
        # Create a crop recommendation request
        request = DataRequest(
            request_id=str(uuid.uuid4()),
            category=DataCategory.HYBRID_COMPUTED,
            data_type="crop_recommendation",
            location=location,
            farmer_id="FARM001",
            parameters={"season": "kharif"},
            priority=DataPriority.HIGH
        )
        
        # Process request
        response = await coordinator.process_data_request(request)
        
        if response.success:
            print("Crop Recommendation Response:")
            print(f"Processing Time: {response.processing_time:.2f}s")
            print(f"Recommended Crops: {len(response.data.get('crop_recommendation', {}).get('recommended_crops', []))}")
        else:
            print(f"Request failed: {response.error}")
        
        # Get performance report
        report = await coordinator.get_performance_report()
        print(f"Performance Report: {report['performance_metrics']}")
        
    finally:
        await coordinator.cleanup_resources()

if __name__ == "__main__":
    asyncio.run(main())