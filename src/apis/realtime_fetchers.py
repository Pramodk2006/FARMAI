# STEP 2: API Fetchers for Category 2 Data (Real-time)

import asyncio
import aiohttp
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """Configuration for API endpoints"""
    base_url: str
    api_key: str
    rate_limit: int = 60  # requests per minute
    timeout: int = 30  # seconds

class BaseAPIFetcher(ABC):
    """Abstract base class for API fetchers"""
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_time = 0
        self.request_count = 0
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit_check(self):
        """Implement rate limiting"""
        current_time = datetime.now().timestamp()
        if current_time - self.last_request_time < 60:  # Same minute
            if self.request_count >= self.config.rate_limit:
                sleep_time = 60 - (current_time - self.last_request_time)
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
                self.request_count = 0
                self.last_request_time = current_time
        else:
            self.request_count = 0
            self.last_request_time = current_time
        
        self.request_count += 1
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        await self._rate_limit_check()
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        headers = {
            "User-Agent": "Agricultural-AI-System/1.0",
            "Accept": "application/json"
        }
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        url = f"{self.config.base_url}/{endpoint}"
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                return data
                
        except aiohttp.ClientError as e:
            logger.error(f"API request failed for {url}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response from {url}: {e}")
            raise
    
    @abstractmethod
    async def fetch_data(self, **kwargs) -> Dict[str, Any]:
        """Fetch data from the API"""
        pass

class WeatherAPIFetcher(BaseAPIFetcher):
    """Fetcher for weather data APIs (OpenWeatherMap, AccuWeather, etc.)"""
    
    def __init__(self, config: APIConfig):
        super().__init__(config)
        self.units = "metric"  # celsius, m/s, hPa
    
    async def fetch_current_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Fetch current weather data for given coordinates
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Current weather data
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self.config.api_key,
            "units": self.units
        }
        
        try:
            data = await self._make_request("weather", params)
            
            # Process and standardize weather data
            processed_data = {
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "city": data.get("name", "Unknown"),
                    "country": data.get("sys", {}).get("country", "Unknown")
                },
                "current_conditions": {
                    "temperature": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "humidity": data["main"]["humidity"],
                    "pressure": data["main"]["pressure"],
                    "visibility": data.get("visibility", 0) / 1000,  # Convert to km
                    "uv_index": None,  # Not available in current weather API
                    "wind_speed": data["wind"]["speed"],
                    "wind_direction": data["wind"].get("deg", 0),
                    "cloud_cover": data["clouds"]["all"],
                    "weather_condition": data["weather"][0]["main"],
                    "weather_description": data["weather"][0]["description"],
                    "precipitation": {
                        "rain_1h": data.get("rain", {}).get("1h", 0),
                        "snow_1h": data.get("snow", {}).get("1h", 0)
                    }
                },
                "sun_info": {
                    "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]),
                    "sunset": datetime.fromtimestamp(data["sys"]["sunset"])
                },
                "timestamp": datetime.fromtimestamp(data["dt"]),
                "data_source": "openweathermap",
                "api_version": "2.5"
            }
            
            logger.info(f"Fetched current weather for {latitude}, {longitude}")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching current weather: {e}")
            raise
    
    async def fetch_weather_forecast(self, latitude: float, longitude: float, days: int = 5) -> Dict[str, Any]:
        """
        Fetch weather forecast
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            days: Number of forecast days
            
        Returns:
            Weather forecast data
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self.config.api_key,
            "units": self.units,
            "cnt": days * 8  # 8 forecasts per day (3-hour intervals)
        }
        
        try:
            data = await self._make_request("forecast", params)
            
            # Process forecast data
            forecasts = []
            for item in data["list"]:
                forecast_item = {
                    "datetime": datetime.fromtimestamp(item["dt"]),
                    "temperature": {
                        "current": item["main"]["temp"],
                        "min": item["main"]["temp_min"],
                        "max": item["main"]["temp_max"],
                        "feels_like": item["main"]["feels_like"]
                    },
                    "humidity": item["main"]["humidity"],
                    "pressure": item["main"]["pressure"],
                    "wind_speed": item["wind"]["speed"],
                    "wind_direction": item["wind"].get("deg", 0),
                    "cloud_cover": item["clouds"]["all"],
                    "weather_condition": item["weather"][0]["main"],
                    "weather_description": item["weather"][0]["description"],
                    "precipitation_probability": item.get("pop", 0) * 100,
                    "precipitation": {
                        "rain_3h": item.get("rain", {}).get("3h", 0),
                        "snow_3h": item.get("snow", {}).get("3h", 0)
                    }
                }
                forecasts.append(forecast_item)
            
            processed_data = {
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "city": data["city"]["name"],
                    "country": data["city"]["country"]
                },
                "forecast_count": len(forecasts),
                "forecast_days": days,
                "forecasts": forecasts,
                "timestamp": datetime.utcnow(),
                "data_source": "openweathermap",
                "api_version": "2.5"
            }
            
            logger.info(f"Fetched {days}-day weather forecast for {latitude}, {longitude}")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching weather forecast: {e}")
            raise
    
    async def fetch_data(self, **kwargs) -> Dict[str, Any]:
        """Generic fetch data method"""
        latitude = kwargs.get("latitude")
        longitude = kwargs.get("longitude")
        forecast = kwargs.get("forecast", False)
        
        if forecast:
            return await self.fetch_weather_forecast(latitude, longitude)
        else:
            return await self.fetch_current_weather(latitude, longitude)

class MarketPriceAPIFetcher(BaseAPIFetcher):
    """Fetcher for agricultural market price data"""
    
    async def fetch_commodity_prices(self, commodity: str, market: str = None, state: str = None) -> Dict[str, Any]:
        """
        Fetch commodity prices from agricultural market APIs
        
        Args:
            commodity: Commodity name (e.g., "wheat", "rice", "tomato")
            market: Specific market name
            state: State name
            
        Returns:
            Market price data
        """
        params = {
            "commodity": commodity,
            "api_key": self.config.api_key
        }
        
        if market:
            params["market"] = market
        if state:
            params["state"] = state
        
        try:
            data = await self._make_request("commodity-prices", params)
            
            processed_data = {
                "commodity": commodity,
                "market_info": {
                    "market_name": market or "All Markets",
                    "state": state or "All States",
                    "country": "India"
                },
                "price_data": {
                    "min_price": data.get("min_price", 0),
                    "max_price": data.get("max_price", 0),
                    "modal_price": data.get("modal_price", 0),
                    "price_unit": data.get("price_unit", "per quintal"),
                    "currency": "INR"
                },
                "market_trends": {
                    "price_change": data.get("price_change", 0),
                    "price_change_percent": data.get("price_change_percent", 0),
                    "trend_direction": data.get("trend", "stable")
                },
                "trading_info": {
                    "arrivals": data.get("arrivals", 0),
                    "trading_date": data.get("trading_date"),
                    "market_status": data.get("market_status", "open")
                },
                "timestamp": datetime.utcnow(),
                "data_source": "market_api"
            }
            
            logger.info(f"Fetched market prices for {commodity}")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching commodity prices: {e}")
            raise
    
    async def fetch_data(self, **kwargs) -> Dict[str, Any]:
        """Generic fetch data method"""
        commodity = kwargs.get("commodity", "wheat")
        market = kwargs.get("market")
        state = kwargs.get("state")
        
        return await self.fetch_commodity_prices(commodity, market, state)

class SatelliteImageryFetcher(BaseAPIFetcher):
    """Fetcher for satellite imagery and remote sensing data"""
    
    async def fetch_ndvi_data(self, latitude: float, longitude: float, 
                              start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch NDVI (Normalized Difference Vegetation Index) data
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            NDVI data
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "appid": self.config.api_key
        }
        
        try:
            data = await self._make_request("ndvi_history", params)
            
            processed_data = {
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "ndvi_data": [],
                "statistics": {
                    "avg_ndvi": 0,
                    "max_ndvi": 0,
                    "min_ndvi": 1,
                    "data_points": len(data.get("data", []))
                },
                "timestamp": datetime.utcnow(),
                "data_source": "satellite_api"
            }
            
            # Process NDVI values
            ndvi_values = []
            for item in data.get("data", []):
                ndvi_point = {
                    "date": datetime.fromtimestamp(item["dt"]),
                    "ndvi": item["data"]["ndvi"],
                    "cloud_cover": item["data"].get("clouds", 0)
                }
                processed_data["ndvi_data"].append(ndvi_point)
                if item["data"]["ndvi"] is not None:
                    ndvi_values.append(item["data"]["ndvi"])
            
            # Calculate statistics
            if ndvi_values:
                processed_data["statistics"]["avg_ndvi"] = sum(ndvi_values) / len(ndvi_values)
                processed_data["statistics"]["max_ndvi"] = max(ndvi_values)
                processed_data["statistics"]["min_ndvi"] = min(ndvi_values)
            
            logger.info(f"Fetched NDVI data for {latitude}, {longitude}")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching NDVI data: {e}")
            raise
    
    async def fetch_data(self, **kwargs) -> Dict[str, Any]:
        """Generic fetch data method"""
        latitude = kwargs.get("latitude")
        longitude = kwargs.get("longitude")
        start_date = kwargs.get("start_date", datetime.now() - timedelta(days=30))
        end_date = kwargs.get("end_date", datetime.now())
        
        return await self.fetch_ndvi_data(latitude, longitude, start_date, end_date)

class PestAlertAPIFetcher(BaseAPIFetcher):
    """Fetcher for pest and disease alert data"""
    
    async def fetch_pest_alerts(self, crop_type: str, region: str, 
                               alert_level: str = "all") -> Dict[str, Any]:
        """
        Fetch pest and disease alerts
        
        Args:
            crop_type: Type of crop
            region: Geographic region
            alert_level: Alert level filter ("low", "medium", "high", "all")
            
        Returns:
            Pest alert data
        """
        params = {
            "crop": crop_type,
            "region": region,
            "level": alert_level,
            "api_key": self.config.api_key
        }
        
        try:
            data = await self._make_request("pest-alerts", params)
            
            processed_alerts = []
            for alert in data.get("alerts", []):
                processed_alert = {
                    "alert_id": alert["id"],
                    "pest_name": alert["pest_name"],
                    "pest_type": alert["pest_type"],  # insect, disease, weed
                    "severity_level": alert["severity"],
                    "affected_crop": alert["crop"],
                    "symptoms": alert["symptoms"],
                    "management_advice": alert["management"],
                    "geographic_scope": alert["region"],
                    "alert_date": datetime.fromisoformat(alert["date"]),
                    "valid_until": datetime.fromisoformat(alert["valid_until"]),
                    "weather_factors": alert.get("weather_factors", {}),
                    "preventive_measures": alert.get("preventive_measures", []),
                    "treatment_options": alert.get("treatments", [])
                }
                processed_alerts.append(processed_alert)
            
            processed_data = {
                "crop_type": crop_type,
                "region": region,
                "alert_level_filter": alert_level,
                "total_alerts": len(processed_alerts),
                "active_alerts": processed_alerts,
                "risk_assessment": {
                    "overall_risk": data.get("overall_risk", "medium"),
                    "risk_factors": data.get("risk_factors", []),
                    "recommended_actions": data.get("recommendations", [])
                },
                "timestamp": datetime.utcnow(),
                "data_source": "pest_alert_api"
            }
            
            logger.info(f"Fetched {len(processed_alerts)} pest alerts for {crop_type} in {region}")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching pest alerts: {e}")
            raise
    
    async def fetch_data(self, **kwargs) -> Dict[str, Any]:
        """Generic fetch data method"""
        crop_type = kwargs.get("crop_type", "wheat")
        region = kwargs.get("region", "india")
        alert_level = kwargs.get("alert_level", "all")
        
        return await self.fetch_pest_alerts(crop_type, region, alert_level)

class GovernmentSchemesFetcher(BaseAPIFetcher):
    """Fetcher for government schemes and subsidies data"""
    
    async def fetch_active_schemes(self, state: str = None, category: str = None) -> Dict[str, Any]:
        """
        Fetch active government schemes
        
        Args:
            state: State name filter
            category: Scheme category (subsidy, insurance, loan, etc.)
            
        Returns:
            Government schemes data
        """
        params = {
            "status": "active",
            "api_key": self.config.api_key
        }
        
        if state:
            params["state"] = state
        if category:
            params["category"] = category
        
        try:
            data = await self._make_request("government-schemes", params)
            
            processed_schemes = []
            for scheme in data.get("schemes", []):
                processed_scheme = {
                    "scheme_id": scheme["id"],
                    "scheme_name": scheme["name"],
                    "description": scheme["description"],
                    "category": scheme["category"],
                    "implementing_agency": scheme["agency"],
                    "target_beneficiaries": scheme["beneficiaries"],
                    "eligibility_criteria": scheme["eligibility"],
                    "benefits": scheme["benefits"],
                    "application_process": scheme["application"],
                    "required_documents": scheme["documents"],
                    "geographic_coverage": scheme["coverage"],
                    "launch_date": datetime.fromisoformat(scheme["launch_date"]),
                    "deadline": datetime.fromisoformat(scheme["deadline"]) if scheme.get("deadline") else None,
                    "budget_allocated": scheme.get("budget", 0),
                    "contact_info": scheme.get("contact", {}),
                    "website_url": scheme.get("website", ""),
                    "status": scheme["status"]
                }
                processed_schemes.append(processed_scheme)
            
            processed_data = {
                "state_filter": state or "All States",
                "category_filter": category or "All Categories",
                "total_schemes": len(processed_schemes),
                "active_schemes": processed_schemes,
                "categories_available": list(set(s["category"] for s in processed_schemes)),
                "timestamp": datetime.utcnow(),
                "data_source": "government_schemes_api"
            }
            
            logger.info(f"Fetched {len(processed_schemes)} government schemes")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching government schemes: {e}")
            raise
    
    async def fetch_data(self, **kwargs) -> Dict[str, Any]:
        """Generic fetch data method"""
        state = kwargs.get("state")
        category = kwargs.get("category")
        
        return await self.fetch_active_schemes(state, category)

class RealTimeDataFetcher:
    """Main coordinator for all real-time API fetchers"""
    
    def __init__(self):
        self.fetchers: Dict[str, BaseAPIFetcher] = {}
        self._load_configurations()
    
    def _load_configurations(self):
        """Load API configurations from environment variables"""
        
        # Weather API configuration
        weather_config = APIConfig(
            base_url=os.getenv("WEATHER_API_BASE_URL", "https://api.openweathermap.org/data/2.5"),
            api_key=os.getenv("WEATHER_API_KEY", ""),
            rate_limit=60
        )
        
        # Market API configuration
        market_config = APIConfig(
            base_url=os.getenv("MARKET_API_BASE_URL", "https://api.data.gov.in/resource"),
            api_key=os.getenv("MARKET_API_KEY", ""),
            rate_limit=100
        )
        
        # Satellite API configuration
        satellite_config = APIConfig(
            base_url=os.getenv("SATELLITE_API_BASE_URL", "http://api.agromonitoring.com/agro/1.0"),
            api_key=os.getenv("SATELLITE_API_KEY", ""),
            rate_limit=1000
        )
        
        # Pest API configuration
        pest_config = APIConfig(
            base_url=os.getenv("PEST_API_BASE_URL", "https://api.pestnet.org/v1"),
            api_key=os.getenv("PEST_API_KEY", ""),
            rate_limit=500
        )
        
        # Government schemes API configuration
        schemes_config = APIConfig(
            base_url=os.getenv("SCHEMES_API_BASE_URL", "https://api.gov.in/schemes"),
            api_key=os.getenv("SCHEMES_API_KEY", ""),
            rate_limit=200
        )
        
        # Initialize fetchers
        self.fetchers = {
            "weather": WeatherAPIFetcher(weather_config),
            "market": MarketPriceAPIFetcher(market_config),
            "satellite": SatelliteImageryFetcher(satellite_config),
            "pest": PestAlertAPIFetcher(pest_config),
            "schemes": GovernmentSchemesFetcher(schemes_config)
        }
    
    async def fetch_all_data(self, location: Dict[str, float], **kwargs) -> Dict[str, Any]:
        """
        Fetch data from all configured APIs
        
        Args:
            location: Dictionary with latitude and longitude
            **kwargs: Additional parameters for specific APIs
            
        Returns:
            Combined data from all APIs
        """
        results = {}
        
        async def fetch_with_error_handling(name: str, fetcher: BaseAPIFetcher):
            try:
                async with fetcher:
                    if name == "weather":
                        data = await fetcher.fetch_data(
                            latitude=location["latitude"],
                            longitude=location["longitude"]
                        )
                    elif name == "satellite":
                        data = await fetcher.fetch_data(
                            latitude=location["latitude"],
                            longitude=location["longitude"],
                            start_date=kwargs.get("start_date"),
                            end_date=kwargs.get("end_date")
                        )
                    elif name == "market":
                        data = await fetcher.fetch_data(
                            commodity=kwargs.get("commodity", "wheat"),
                            state=kwargs.get("state")
                        )
                    elif name == "pest":
                        data = await fetcher.fetch_data(
                            crop_type=kwargs.get("crop_type", "wheat"),
                            region=kwargs.get("region", "india")
                        )
                    elif name == "schemes":
                        data = await fetcher.fetch_data(
                            state=kwargs.get("state"),
                            category=kwargs.get("scheme_category")
                        )
                    else:
                        data = await fetcher.fetch_data(**kwargs)
                    
                    results[name] = {
                        "success": True,
                        "data": data,
                        "timestamp": datetime.utcnow()
                    }
                    
            except Exception as e:
                logger.error(f"Error fetching {name} data: {e}")
                results[name] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow()
                }
        
        # Fetch data from all APIs concurrently
        tasks = [
            fetch_with_error_handling(name, fetcher) 
            for name, fetcher in self.fetchers.items()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Compile summary
        successful_fetches = sum(1 for result in results.values() if result["success"])
        
        final_results = {
            "fetch_summary": {
                "total_apis": len(self.fetchers),
                "successful_fetches": successful_fetches,
                "failed_fetches": len(self.fetchers) - successful_fetches,
                "fetch_timestamp": datetime.utcnow()
            },
            "location": location,
            "data": results
        }
        
        logger.info(f"Completed real-time data fetch: {successful_fetches}/{len(self.fetchers)} APIs successful")
        return final_results

# Example usage
async def main():
    """Example usage of real-time data fetchers"""
    
    fetcher = RealTimeDataFetcher()
    
    # Example location (Delhi, India)
    location = {
        "latitude": 28.6139,
        "longitude": 77.2090
    }
    
    # Fetch all real-time data
    all_data = await fetcher.fetch_all_data(
        location=location,
        crop_type="wheat",
        commodity="wheat",
        state="Delhi",
        region="north_india"
    )
    
    print(f"Fetch Summary: {all_data['fetch_summary']}")
    
    # Print weather data if successful
    if all_data["data"]["weather"]["success"]:
        weather = all_data["data"]["weather"]["data"]
        print(f"Current Temperature: {weather['current_conditions']['temperature']}°C")
        print(f"Weather: {weather['current_conditions']['weather_description']}")

if __name__ == "__main__":
    asyncio.run(main())