# STEP 3: Hybrid Data Managers for Category 3 Data (Soil Health, Rainfall Patterns)

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from scipy import interpolate, stats
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SoilDataPoint:
    """Individual soil measurement data point"""
    timestamp: datetime
    location: Dict[str, float]  # latitude, longitude
    soil_moisture: float  # percentage
    soil_temperature: float  # celsius
    ph_level: float  # pH scale
    nitrogen: float  # ppm
    phosphorus: float  # ppm
    potassium: float  # ppm
    organic_matter: float  # percentage
    electrical_conductivity: float  # dS/m
    bulk_density: float  # g/cm³
    data_source: str = "sensor"
    quality_score: float = 1.0

@dataclass
class RainfallDataPoint:
    """Individual rainfall measurement data point"""
    timestamp: datetime
    location: Dict[str, float]
    precipitation: float  # mm
    intensity: float  # mm/hour
    duration: int  # minutes
    temperature: float  # celsius
    humidity: float  # percentage
    pressure: float  # hPa
    data_source: str = "weather_station"
    quality_score: float = 1.0

@dataclass
class SoilHealthIndex:
    """Soil health assessment result"""
    overall_score: float  # 0-100
    moisture_status: str  # "optimal", "low", "high", "critical"
    nutrient_status: Dict[str, str]  # nutrient: status
    ph_status: str  # "acidic", "neutral", "alkaline"
    organic_matter_status: str  # "low", "medium", "high"
    recommendations: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    calculated_at: datetime = field(default_factory=datetime.utcnow)

class SoilHealthManager:
    """Manager for soil health data integration and analysis"""
    
    def __init__(self):
        self.soil_data: List[SoilDataPoint] = []
        self.historical_data: pd.DataFrame = pd.DataFrame()
        self.soil_models = {}
        self.reference_ranges = self._load_reference_ranges()
    
    def _load_reference_ranges(self) -> Dict[str, Dict[str, float]]:
        """Load reference ranges for soil parameters"""
        return {
            "soil_moisture": {
                "very_low": 10.0,
                "low": 20.0,
                "optimal_min": 25.0,
                "optimal_max": 35.0,
                "high": 45.0,
                "very_high": 60.0
            },
            "ph_level": {
                "very_acidic": 4.5,
                "acidic": 5.5,
                "slightly_acidic": 6.0,
                "neutral_min": 6.5,
                "neutral_max": 7.5,
                "slightly_alkaline": 8.0,
                "alkaline": 8.5,
                "very_alkaline": 9.0
            },
            "nitrogen": {
                "very_low": 20.0,
                "low": 40.0,
                "medium": 60.0,
                "high": 80.0,
                "very_high": 100.0
            },
            "phosphorus": {
                "very_low": 10.0,
                "low": 20.0,
                "medium": 35.0,
                "high": 50.0,
                "very_high": 70.0
            },
            "potassium": {
                "very_low": 50.0,
                "low": 100.0,
                "medium": 150.0,
                "high": 200.0,
                "very_high": 280.0
            },
            "organic_matter": {
                "very_low": 1.0,
                "low": 2.0,
                "medium": 3.0,
                "high": 5.0,
                "very_high": 7.0
            }
        }
    
    async def add_soil_data(self, soil_data: List[Dict[str, Any]]):
        """
        Add new soil measurement data
        
        Args:
            soil_data: List of soil measurement dictionaries
        """
        try:
            for data in soil_data:
                soil_point = SoilDataPoint(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    location=data["location"],
                    soil_moisture=data["soil_moisture"],
                    soil_temperature=data["soil_temperature"],
                    ph_level=data["ph_level"],
                    nitrogen=data["nitrogen"],
                    phosphorus=data["phosphorus"],
                    potassium=data["potassium"],
                    organic_matter=data["organic_matter"],
                    electrical_conductivity=data.get("electrical_conductivity", 0.0),
                    bulk_density=data.get("bulk_density", 1.3),
                    data_source=data.get("data_source", "sensor"),
                    quality_score=data.get("quality_score", 1.0)
                )
                
                # Validate data quality
                if await self._validate_soil_data(soil_point):
                    self.soil_data.append(soil_point)
                    logger.info(f"Added soil data point from {soil_point.timestamp}")
                else:
                    logger.warning(f"Soil data validation failed for timestamp {data['timestamp']}")
            
            # Update historical dataframe
            await self._update_historical_dataframe()
            
        except Exception as e:
            logger.error(f"Error adding soil data: {e}")
            raise
    
    async def _validate_soil_data(self, soil_point: SoilDataPoint) -> bool:
        """
        Validate soil data point for reasonable values
        
        Args:
            soil_point: Soil data point to validate
            
        Returns:
            True if data is valid
        """
        validation_rules = {
            "soil_moisture": (0, 100),
            "soil_temperature": (-10, 60),
            "ph_level": (3.0, 12.0),
            "nitrogen": (0, 500),
            "phosphorus": (0, 200),
            "potassium": (0, 1000),
            "organic_matter": (0, 20),
            "electrical_conductivity": (0, 10),
            "bulk_density": (0.8, 2.0)
        }
        
        for param, (min_val, max_val) in validation_rules.items():
            value = getattr(soil_point, param)
            if not (min_val <= value <= max_val):
                logger.warning(f"Invalid {param} value: {value} (expected {min_val}-{max_val})")
                return False
        
        return True
    
    async def _update_historical_dataframe(self):
        """Update historical data DataFrame"""
        if self.soil_data:
            records = []
            for point in self.soil_data:
                record = {
                    "timestamp": point.timestamp,
                    "latitude": point.location["latitude"],
                    "longitude": point.location["longitude"],
                    "soil_moisture": point.soil_moisture,
                    "soil_temperature": point.soil_temperature,
                    "ph_level": point.ph_level,
                    "nitrogen": point.nitrogen,
                    "phosphorus": point.phosphorus,
                    "potassium": point.potassium,
                    "organic_matter": point.organic_matter,
                    "electrical_conductivity": point.electrical_conductivity,
                    "bulk_density": point.bulk_density,
                    "data_source": point.data_source,
                    "quality_score": point.quality_score
                }
                records.append(record)
            
            self.historical_data = pd.DataFrame(records)
            self.historical_data = self.historical_data.sort_values("timestamp")
            logger.info(f"Updated historical data with {len(records)} records")
    
    async def calculate_soil_health_index(self, location: Dict[str, float], 
                                        time_window_days: int = 30) -> SoilHealthIndex:
        """
        Calculate comprehensive soil health index
        
        Args:
            location: Location coordinates
            time_window_days: Time window for analysis in days
            
        Returns:
            Soil health index
        """
        try:
            # Filter data by location and time
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=time_window_days)
            
            filtered_data = self._filter_data_by_location_and_time(
                location, start_date, end_date
            )
            
            if filtered_data.empty:
                logger.warning(f"No soil data found for location {location}")
                return SoilHealthIndex(overall_score=0, moisture_status="unknown",
                                     nutrient_status={}, ph_status="unknown",
                                     organic_matter_status="unknown")
            
            # Calculate individual parameter scores
            moisture_score, moisture_status = self._assess_soil_moisture(filtered_data)
            ph_score, ph_status = self._assess_ph_level(filtered_data)
            nutrient_scores, nutrient_status = self._assess_nutrients(filtered_data)
            organic_score, organic_status = self._assess_organic_matter(filtered_data)
            
            # Calculate overall score (weighted average)
            weights = {
                "moisture": 0.25,
                "ph": 0.20,
                "nutrients": 0.35,  # Combined N, P, K
                "organic_matter": 0.20
            }
            
            overall_score = (
                moisture_score * weights["moisture"] +
                ph_score * weights["ph"] +
                np.mean(list(nutrient_scores.values())) * weights["nutrients"] +
                organic_score * weights["organic_matter"]
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                moisture_status, ph_status, nutrient_status, organic_status
            )
            
            # Identify risk factors
            risk_factors = self._identify_risk_factors(
                moisture_status, ph_status, nutrient_status, organic_status
            )
            
            soil_health_index = SoilHealthIndex(
                overall_score=round(overall_score, 2),
                moisture_status=moisture_status,
                nutrient_status=nutrient_status,
                ph_status=ph_status,
                organic_matter_status=organic_status,
                recommendations=recommendations,
                risk_factors=risk_factors
            )
            
            logger.info(f"Calculated soil health index: {overall_score:.2f}")
            return soil_health_index
            
        except Exception as e:
            logger.error(f"Error calculating soil health index: {e}")
            raise
    
    def _filter_data_by_location_and_time(self, location: Dict[str, float], 
                                        start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Filter historical data by location and time window"""
        if self.historical_data.empty:
            return pd.DataFrame()
        
        # Define location tolerance (approximately 1 km)
        lat_tolerance = 0.01
        lon_tolerance = 0.01
        
        filtered = self.historical_data[
            (self.historical_data["timestamp"] >= start_date) &
            (self.historical_data["timestamp"] <= end_date) &
            (abs(self.historical_data["latitude"] - location["latitude"]) <= lat_tolerance) &
            (abs(self.historical_data["longitude"] - location["longitude"]) <= lon_tolerance)
        ]
        
        return filtered
    
    def _assess_soil_moisture(self, data: pd.DataFrame) -> Tuple[float, str]:
        """Assess soil moisture status and score"""
        if data.empty:
            return 0, "unknown"
        
        avg_moisture = data["soil_moisture"].mean()
        ranges = self.reference_ranges["soil_moisture"]
        
        if avg_moisture < ranges["very_low"]:
            return 20, "very_low"
        elif avg_moisture < ranges["low"]:
            return 40, "low"
        elif ranges["optimal_min"] <= avg_moisture <= ranges["optimal_max"]:
            return 100, "optimal"
        elif avg_moisture < ranges["high"]:
            return 80, "slightly_high"
        elif avg_moisture < ranges["very_high"]:
            return 60, "high"
        else:
            return 30, "very_high"
    
    def _assess_ph_level(self, data: pd.DataFrame) -> Tuple[float, str]:
        """Assess soil pH status and score"""
        if data.empty:
            return 0, "unknown"
        
        avg_ph = data["ph_level"].mean()
        ranges = self.reference_ranges["ph_level"]
        
        if avg_ph < ranges["very_acidic"]:
            return 30, "very_acidic"
        elif avg_ph < ranges["acidic"]:
            return 50, "acidic"
        elif avg_ph < ranges["slightly_acidic"]:
            return 70, "slightly_acidic"
        elif ranges["neutral_min"] <= avg_ph <= ranges["neutral_max"]:
            return 100, "neutral"
        elif avg_ph < ranges["slightly_alkaline"]:
            return 80, "slightly_alkaline"
        elif avg_ph < ranges["alkaline"]:
            return 60, "alkaline"
        else:
            return 40, "very_alkaline"
    
    def _assess_nutrients(self, data: pd.DataFrame) -> Tuple[Dict[str, float], Dict[str, str]]:
        """Assess nutrient levels (N, P, K)"""
        if data.empty:
            return {}, {}
        
        nutrients = ["nitrogen", "phosphorus", "potassium"]
        scores = {}
        statuses = {}
        
        for nutrient in nutrients:
            avg_value = data[nutrient].mean()
            ranges = self.reference_ranges[nutrient]
            
            if avg_value < ranges["very_low"]:
                scores[nutrient] = 20
                statuses[nutrient] = "very_low"
            elif avg_value < ranges["low"]:
                scores[nutrient] = 40
                statuses[nutrient] = "low"
            elif avg_value < ranges["medium"]:
                scores[nutrient] = 70
                statuses[nutrient] = "medium"
            elif avg_value < ranges["high"]:
                scores[nutrient] = 90
                statuses[nutrient] = "high"
            else:
                scores[nutrient] = 100
                statuses[nutrient] = "very_high"
        
        return scores, statuses
    
    def _assess_organic_matter(self, data: pd.DataFrame) -> Tuple[float, str]:
        """Assess organic matter content"""
        if data.empty:
            return 0, "unknown"
        
        avg_organic = data["organic_matter"].mean()
        ranges = self.reference_ranges["organic_matter"]
        
        if avg_organic < ranges["very_low"]:
            return 30, "very_low"
        elif avg_organic < ranges["low"]:
            return 50, "low"
        elif avg_organic < ranges["medium"]:
            return 70, "medium"
        elif avg_organic < ranges["high"]:
            return 90, "high"
        else:
            return 100, "very_high"
    
    def _generate_recommendations(self, moisture_status: str, ph_status: str,
                                nutrient_status: Dict[str, str], organic_status: str) -> List[str]:
        """Generate soil management recommendations"""
        recommendations = []
        
        # Moisture recommendations
        if moisture_status in ["very_low", "low"]:
            recommendations.append("Increase irrigation frequency and consider mulching to retain soil moisture")
        elif moisture_status in ["high", "very_high"]:
            recommendations.append("Improve drainage and reduce irrigation to prevent waterlogging")
        
        # pH recommendations
        if ph_status in ["very_acidic", "acidic"]:
            recommendations.append("Apply lime to increase soil pH and reduce acidity")
        elif ph_status in ["alkaline", "very_alkaline"]:
            recommendations.append("Apply sulfur or organic matter to reduce soil pH")
        
        # Nutrient recommendations
        if nutrient_status.get("nitrogen") in ["very_low", "low"]:
            recommendations.append("Apply nitrogen-rich fertilizers or organic compost")
        if nutrient_status.get("phosphorus") in ["very_low", "low"]:
            recommendations.append("Apply phosphorus fertilizers, preferably rock phosphate")
        if nutrient_status.get("potassium") in ["very_low", "low"]:
            recommendations.append("Apply potassium-rich fertilizers or wood ash")
        
        # Organic matter recommendations
        if organic_status in ["very_low", "low"]:
            recommendations.append("Incorporate organic matter through compost, crop residues, or green manure")
        
        return recommendations
    
    def _identify_risk_factors(self, moisture_status: str, ph_status: str,
                             nutrient_status: Dict[str, str], organic_status: str) -> List[str]:
        """Identify potential risk factors"""
        risks = []
        
        if moisture_status == "very_low":
            risks.append("High drought stress risk")
        elif moisture_status == "very_high":
            risks.append("Waterlogging and root rot risk")
        
        if ph_status in ["very_acidic", "very_alkaline"]:
            risks.append("Nutrient availability problems due to extreme pH")
        
        low_nutrients = [nutrient for nutrient, status in nutrient_status.items() 
                        if status in ["very_low", "low"]]
        if low_nutrients:
            risks.append(f"Nutrient deficiency risk: {', '.join(low_nutrients)}")
        
        if organic_status in ["very_low", "low"]:
            risks.append("Poor soil structure and reduced water retention capacity")
        
        return risks

class RainfallPatternManager:
    """Manager for rainfall pattern analysis and prediction"""
    
    def __init__(self):
        self.rainfall_data: List[RainfallDataPoint] = []
        self.historical_data: pd.DataFrame = pd.DataFrame()
        self.pattern_models = {}
    
    async def add_rainfall_data(self, rainfall_data: List[Dict[str, Any]]):
        """
        Add new rainfall measurement data
        
        Args:
            rainfall_data: List of rainfall measurement dictionaries
        """
        try:
            for data in rainfall_data:
                rainfall_point = RainfallDataPoint(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    location=data["location"],
                    precipitation=data["precipitation"],
                    intensity=data.get("intensity", 0.0),
                    duration=data.get("duration", 0),
                    temperature=data.get("temperature", 25.0),
                    humidity=data.get("humidity", 50.0),
                    pressure=data.get("pressure", 1013.25),
                    data_source=data.get("data_source", "weather_station"),
                    quality_score=data.get("quality_score", 1.0)
                )
                
                if await self._validate_rainfall_data(rainfall_point):
                    self.rainfall_data.append(rainfall_point)
                    logger.info(f"Added rainfall data point from {rainfall_point.timestamp}")
            
            # Update historical dataframe
            await self._update_rainfall_dataframe()
            
        except Exception as e:
            logger.error(f"Error adding rainfall data: {e}")
            raise
    
    async def _validate_rainfall_data(self, rainfall_point: RainfallDataPoint) -> bool:
        """Validate rainfall data point"""
        validation_rules = {
            "precipitation": (0, 500),  # mm
            "intensity": (0, 100),      # mm/hour
            "duration": (0, 1440),      # minutes (max 24 hours)
            "temperature": (-20, 60),    # celsius
            "humidity": (0, 100),        # percentage
            "pressure": (900, 1100)      # hPa
        }
        
        for param, (min_val, max_val) in validation_rules.items():
            value = getattr(rainfall_point, param)
            if not (min_val <= value <= max_val):
                logger.warning(f"Invalid {param} value: {value} (expected {min_val}-{max_val})")
                return False
        
        return True
    
    async def _update_rainfall_dataframe(self):
        """Update historical rainfall DataFrame"""
        if self.rainfall_data:
            records = []
            for point in self.rainfall_data:
                record = {
                    "timestamp": point.timestamp,
                    "latitude": point.location["latitude"],
                    "longitude": point.location["longitude"],
                    "precipitation": point.precipitation,
                    "intensity": point.intensity,
                    "duration": point.duration,
                    "temperature": point.temperature,
                    "humidity": point.humidity,
                    "pressure": point.pressure,
                    "data_source": point.data_source,
                    "quality_score": point.quality_score
                }
                records.append(record)
            
            self.historical_data = pd.DataFrame(records)
            self.historical_data = self.historical_data.sort_values("timestamp")
            logger.info(f"Updated rainfall historical data with {len(records)} records")
    
    async def analyze_rainfall_patterns(self, location: Dict[str, float], 
                                      analysis_days: int = 365) -> Dict[str, Any]:
        """
        Analyze rainfall patterns for a specific location
        
        Args:
            location: Location coordinates
            analysis_days: Number of days to analyze
            
        Returns:
            Rainfall pattern analysis
        """
        try:
            # Filter data by location and time
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=analysis_days)
            
            filtered_data = self._filter_rainfall_data(location, start_date, end_date)
            
            if filtered_data.empty:
                logger.warning(f"No rainfall data found for location {location}")
                return {"error": "No data available"}
            
            # Calculate statistics
            stats = self._calculate_rainfall_statistics(filtered_data)
            
            # Identify patterns
            seasonal_patterns = self._analyze_seasonal_patterns(filtered_data)
            intensity_patterns = self._analyze_intensity_patterns(filtered_data)
            dry_periods = self._identify_dry_periods(filtered_data)
            
            # Generate predictions
            predictions = await self._predict_rainfall_trends(filtered_data)
            
            analysis_result = {
                "location": location,
                "analysis_period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "days_analyzed": analysis_days
                },
                "statistics": stats,
                "seasonal_patterns": seasonal_patterns,
                "intensity_patterns": intensity_patterns,
                "dry_periods": dry_periods,
                "predictions": predictions,
                "data_quality": {
                    "total_records": len(filtered_data),
                    "avg_quality_score": filtered_data["quality_score"].mean()
                },
                "analysis_timestamp": datetime.utcnow()
            }
            
            logger.info(f"Completed rainfall pattern analysis for {location}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing rainfall patterns: {e}")
            raise
    
    def _filter_rainfall_data(self, location: Dict[str, float], 
                            start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Filter rainfall data by location and time"""
        if self.historical_data.empty:
            return pd.DataFrame()
        
        lat_tolerance = 0.02
        lon_tolerance = 0.02
        
        filtered = self.historical_data[
            (self.historical_data["timestamp"] >= start_date) &
            (self.historical_data["timestamp"] <= end_date) &
            (abs(self.historical_data["latitude"] - location["latitude"]) <= lat_tolerance) &
            (abs(self.historical_data["longitude"] - location["longitude"]) <= lon_tolerance)
        ]
        
        return filtered
    
    def _calculate_rainfall_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate comprehensive rainfall statistics"""
        if data.empty:
            return {}
        
        # Basic statistics
        total_precipitation = data["precipitation"].sum()
        avg_precipitation = data["precipitation"].mean()
        max_precipitation = data["precipitation"].max()
        rainy_days = len(data[data["precipitation"] > 0])
        total_days = len(data)
        
        # Intensity statistics
        avg_intensity = data[data["intensity"] > 0]["intensity"].mean() if "intensity" in data.columns else 0
        max_intensity = data["intensity"].max() if "intensity" in data.columns else 0
        
        # Variability
        precipitation_std = data["precipitation"].std()
        coefficient_variation = precipitation_std / avg_precipitation if avg_precipitation > 0 else 0
        
        return {
            "total_precipitation_mm": round(total_precipitation, 2),
            "average_daily_precipitation_mm": round(avg_precipitation, 2),
            "maximum_daily_precipitation_mm": round(max_precipitation, 2),
            "rainy_days": rainy_days,
            "total_days": total_days,
            "rainfall_frequency_percent": round((rainy_days / total_days) * 100, 2),
            "average_intensity_mm_per_hour": round(avg_intensity, 2),
            "maximum_intensity_mm_per_hour": round(max_intensity, 2),
            "precipitation_variability": round(coefficient_variation, 2)
        }
    
    def _analyze_seasonal_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze seasonal rainfall patterns"""
        if data.empty:
            return {}
        
        # Group by month
        data["month"] = data["timestamp"].dt.month
        monthly_stats = data.groupby("month")["precipitation"].agg([
            "sum", "mean", "count", "std"
        ]).round(2)
        
        # Identify seasons (for Northern Hemisphere)
        seasons = {
            "spring": [3, 4, 5],
            "summer": [6, 7, 8],
            "autumn": [9, 10, 11],
            "winter": [12, 1, 2]
        }
        
        seasonal_stats = {}
        for season, months in seasons.items():
            season_data = data[data["month"].isin(months)]
            if not season_data.empty:
                seasonal_stats[season] = {
                    "total_precipitation": round(season_data["precipitation"].sum(), 2),
                    "average_precipitation": round(season_data["precipitation"].mean(), 2),
                    "rainy_days": len(season_data[season_data["precipitation"] > 0])
                }
        
        return {
            "monthly_statistics": monthly_stats.to_dict(),
            "seasonal_statistics": seasonal_stats,
            "wettest_month": monthly_stats["sum"].idxmax(),
            "driest_month": monthly_stats["sum"].idxmin()
        }
    
    def _analyze_intensity_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze rainfall intensity patterns"""
        if data.empty or "intensity" not in data.columns:
            return {}
        
        # Classify intensities
        intensity_classes = {
            "light": (0, 2.5),
            "moderate": (2.5, 10),
            "heavy": (10, 50),
            "very_heavy": (50, float("inf"))
        }
        
        intensity_distribution = {}
        for class_name, (min_val, max_val) in intensity_classes.items():
            if max_val == float("inf"):
                class_data = data[data["intensity"] > min_val]
            else:
                class_data = data[(data["intensity"] > min_val) & (data["intensity"] <= max_val)]
            
            intensity_distribution[class_name] = {
                "count": len(class_data),
                "percentage": round((len(class_data) / len(data)) * 100, 2),
                "avg_precipitation": round(class_data["precipitation"].mean(), 2) if not class_data.empty else 0
            }
        
        return {
            "intensity_distribution": intensity_distribution,
            "average_intensity": round(data["intensity"].mean(), 2),
            "maximum_intensity": round(data["intensity"].max(), 2)
        }
    
    def _identify_dry_periods(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Identify consecutive dry periods"""
        if data.empty:
            return {}
        
        # Sort by timestamp
        data_sorted = data.sort_values("timestamp")
        
        # Identify dry days (precipitation <= 1mm)
        dry_days = data_sorted["precipitation"] <= 1.0
        
        # Find consecutive dry periods
        dry_periods = []
        current_period_start = None
        current_period_length = 0
        
        for idx, is_dry in enumerate(dry_days):
            if is_dry:
                if current_period_start is None:
                    current_period_start = data_sorted.iloc[idx]["timestamp"]
                current_period_length += 1
            else:
                if current_period_start is not None:
                    # End of dry period
                    dry_periods.append({
                        "start_date": current_period_start,
                        "end_date": data_sorted.iloc[idx-1]["timestamp"],
                        "duration_days": current_period_length
                    })
                    current_period_start = None
                    current_period_length = 0
        
        # Handle case where data ends with a dry period
        if current_period_start is not None:
            dry_periods.append({
                "start_date": current_period_start,
                "end_date": data_sorted.iloc[-1]["timestamp"],
                "duration_days": current_period_length
            })
        
        if dry_periods:
            max_dry_period = max(dry_periods, key=lambda x: x["duration_days"])
            avg_dry_period = sum(p["duration_days"] for p in dry_periods) / len(dry_periods)
        else:
            max_dry_period = {"duration_days": 0}
            avg_dry_period = 0
        
        return {
            "total_dry_periods": len(dry_periods),
            "longest_dry_period_days": max_dry_period["duration_days"],
            "average_dry_period_days": round(avg_dry_period, 2),
            "dry_periods": dry_periods[-10:]  # Last 10 dry periods
        }
    
    async def _predict_rainfall_trends(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Predict rainfall trends using simple statistical methods"""
        if data.empty or len(data) < 30:
            return {"error": "Insufficient data for predictions"}
        
        try:
            # Simple trend analysis using linear regression
            data_sorted = data.sort_values("timestamp")
            days_since_start = (data_sorted["timestamp"] - data_sorted["timestamp"].min()).dt.days
            
            # Linear trend
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                days_since_start, data_sorted["precipitation"]
            )
            
            # Seasonal decomposition (simplified)
            data_sorted["day_of_year"] = data_sorted["timestamp"].dt.dayofyear
            seasonal_avg = data_sorted.groupby("day_of_year")["precipitation"].mean()
            
            predictions = {
                "trend_analysis": {
                    "slope_mm_per_day": round(slope, 4),
                    "trend_direction": "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable",
                    "correlation_coefficient": round(r_value, 3),
                    "trend_significance": "significant" if p_value < 0.05 else "not_significant"
                },
                "seasonal_forecast": {
                    "next_30_days_avg_precipitation": round(
                        seasonal_avg.iloc[
                            (data_sorted["timestamp"].max().timetuple().tm_yday + 
                             np.arange(30)) % 365
                        ].mean(), 2
                    )
                }
            }
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting rainfall trends: {e}")
            return {"error": str(e)}

class HybridDataManager:
    """Main coordinator for soil health and rainfall pattern managers"""
    
    def __init__(self):
        self.soil_manager = SoilHealthManager()
        self.rainfall_manager = RainfallPatternManager()
    
    async def integrate_data(self, soil_data: List[Dict[str, Any]], 
                           rainfall_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Integrate soil health and rainfall data for comprehensive analysis
        
        Args:
            soil_data: List of soil measurement data
            rainfall_data: List of rainfall measurement data
            
        Returns:
            Integrated analysis results
        """
        try:
            # Add data to respective managers
            await self.soil_manager.add_soil_data(soil_data)
            await self.rainfall_manager.add_rainfall_data(rainfall_data)
            
            # Get location from first data point (assuming same location)
            location = soil_data[0]["location"] if soil_data else rainfall_data[0]["location"]
            
            # Perform analyses
            soil_health = await self.soil_manager.calculate_soil_health_index(location)
            rainfall_patterns = await self.rainfall_manager.analyze_rainfall_patterns(location)
            
            # Cross-correlation analysis
            correlations = await self._analyze_soil_rainfall_correlations(location)
            
            integrated_results = {
                "location": location,
                "soil_health_analysis": soil_health.__dict__,
                "rainfall_pattern_analysis": rainfall_patterns,
                "soil_rainfall_correlations": correlations,
                "integrated_recommendations": self._generate_integrated_recommendations(
                    soil_health, rainfall_patterns
                ),
                "analysis_timestamp": datetime.utcnow()
            }
            
            logger.info("Completed hybrid data integration and analysis")
            return integrated_results
            
        except Exception as e:
            logger.error(f"Error integrating hybrid data: {e}")
            raise
    
    async def _analyze_soil_rainfall_correlations(self, location: Dict[str, float]) -> Dict[str, Any]:
        """Analyze correlations between soil parameters and rainfall"""
        try:
            # Get recent data for both datasets
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=90)
            
            soil_data = self.soil_manager._filter_data_by_location_and_time(
                location, start_date, end_date
            )
            rainfall_data = self.rainfall_manager._filter_rainfall_data(
                location, start_date, end_date
            )
            
            if soil_data.empty or rainfall_data.empty:
                return {"error": "Insufficient data for correlation analysis"}
            
            # Merge datasets by date
            soil_data["date"] = soil_data["timestamp"].dt.date
            rainfall_data["date"] = rainfall_data["timestamp"].dt.date
            
            daily_soil = soil_data.groupby("date").agg({
                "soil_moisture": "mean",
                "soil_temperature": "mean",
                "ph_level": "mean"
            }).reset_index()
            
            daily_rainfall = rainfall_data.groupby("date").agg({
                "precipitation": "sum",
                "intensity": "mean",
                "humidity": "mean"
            }).reset_index()
            
            merged_data = pd.merge(daily_soil, daily_rainfall, on="date", how="inner")
            
            if len(merged_data) < 10:
                return {"error": "Insufficient merged data for correlation analysis"}
            
            # Calculate correlations
            correlations = {}
            soil_params = ["soil_moisture", "soil_temperature", "ph_level"]
            rainfall_params = ["precipitation", "intensity", "humidity"]
            
            for soil_param in soil_params:
                correlations[soil_param] = {}
                for rainfall_param in rainfall_params:
                    corr = merged_data[soil_param].corr(merged_data[rainfall_param])
                    correlations[soil_param][rainfall_param] = round(corr, 3) if not pd.isna(corr) else None
            
            return {
                "correlations": correlations,
                "data_points": len(merged_data),
                "analysis_period": {"start": start_date.date(), "end": end_date.date()}
            }
            
        except Exception as e:
            logger.error(f"Error analyzing correlations: {e}")
            return {"error": str(e)}
    
    def _generate_integrated_recommendations(self, soil_health: SoilHealthIndex, 
                                           rainfall_patterns: Dict[str, Any]) -> List[str]:
        """Generate integrated recommendations based on soil and rainfall analysis"""
        recommendations = []
        
        # Start with soil recommendations
        recommendations.extend(soil_health.recommendations)
        
        # Add rainfall-based recommendations
        if "statistics" in rainfall_patterns:
            stats = rainfall_patterns["statistics"]
            
            if stats.get("rainfall_frequency_percent", 0) < 20:
                recommendations.append("Consider drought-resistant crop varieties due to low rainfall frequency")
            
            if stats.get("maximum_intensity_mm_per_hour", 0) > 50:
                recommendations.append("Implement erosion control measures due to high-intensity rainfall events")
        
        # Cross-factor recommendations
        if soil_health.moisture_status == "low" and rainfall_patterns.get("statistics", {}).get("total_precipitation_mm", 0) < 500:
            recommendations.append("Install water harvesting systems to supplement low rainfall and soil moisture")
        
        if soil_health.ph_status in ["acidic", "very_acidic"] and rainfall_patterns.get("statistics", {}).get("total_precipitation_mm", 0) > 1000:
            recommendations.append("Monitor soil pH closely as high rainfall may increase acidity")
        
        return recommendations

# Example usage
async def main():
    """Example usage of hybrid data managers"""
    
    manager = HybridDataManager()
    
    # Sample soil data
    soil_data = [{
        "timestamp": "2024-01-15T10:00:00",
        "location": {"latitude": 28.6139, "longitude": 77.2090},
        "soil_moisture": 25.5,
        "soil_temperature": 18.2,
        "ph_level": 6.8,
        "nitrogen": 45.0,
        "phosphorus": 25.0,
        "potassium": 120.0,
        "organic_matter": 2.8,
        "electrical_conductivity": 1.2,
        "bulk_density": 1.35
    }]
    
    # Sample rainfall data
    rainfall_data = [{
        "timestamp": "2024-01-15T10:00:00",
        "location": {"latitude": 28.6139, "longitude": 77.2090},
        "precipitation": 5.2,
        "intensity": 2.1,
        "duration": 150,
        "temperature": 22.0,
        "humidity": 75.0,
        "pressure": 1012.5
    }]
    
    # Integrate and analyze data
    results = await manager.integrate_data(soil_data, rainfall_data)
    
    print("Soil Health Score:", results["soil_health_analysis"]["overall_score"])
    print("Recommendations:", results["integrated_recommendations"])

if __name__ == "__main__":
    asyncio.run(main())