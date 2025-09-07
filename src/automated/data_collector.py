# STEP 6: Automated Data Collection System

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import schedule
from concurrent.futures import ThreadPoolExecutor
import time

# Import our custom modules
from src.core.data_coordinator import DataCoordinator, DataRequest, DataCategory, DataPriority
from src.profiling.progressive_workflow import ProgressiveWorkflowManager
from src.database.mongodb_setup import MongoDBSetup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CollectionFrequency(Enum):
    """Data collection frequencies"""
    REAL_TIME = "real_time"      # Every few minutes
    HOURLY = "hourly"            # Every hour
    DAILY = "daily"              # Once per day
    WEEKLY = "weekly"            # Once per week
    MONTHLY = "monthly"          # Once per month
    SEASONAL = "seasonal"        # Per season
    ON_DEMAND = "on_demand"      # When requested

class DataSourceType(Enum):
    """Types of data sources"""
    API_ENDPOINT = "api_endpoint"
    IOT_SENSOR = "iot_sensor"
    USER_INPUT = "user_input"
    CALCULATED = "calculated"
    EXTERNAL_FILE = "external_file"
    SATELLITE = "satellite"

@dataclass
class CollectionJob:
    """Data collection job definition"""
    job_id: str
    job_name: str
    data_type: str
    category: DataCategory
    frequency: CollectionFrequency
    source_type: DataSourceType
    target_farmers: List[str] = field(default_factory=list)  # Empty means all farmers
    collection_parameters: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class CollectionResult:
    """Result of a data collection operation"""
    job_id: str
    farmer_id: str
    success: bool
    data_collected: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    collection_timestamp: datetime = field(default_factory=datetime.utcnow)
    processing_time_seconds: float = 0.0
    data_quality_score: float = 1.0

class AutomatedDataCollector:
    """
    Automated data collection system for agricultural AI
    Handles scheduled collection of various data types from multiple sources
    """
    
    def __init__(self, data_coordinator: DataCoordinator, 
                 workflow_manager: ProgressiveWorkflowManager):
        """
        Initialize automated data collector
        
        Args:
            data_coordinator: Data coordinator instance
            workflow_manager: Progressive workflow manager instance
        """
        self.data_coordinator = data_coordinator
        self.workflow_manager = workflow_manager
        
        # Collection job management
        self.collection_jobs: Dict[str, CollectionJob] = {}
        self.collection_history: List[CollectionResult] = []
        
        # Scheduling and execution
        self.scheduler = schedule
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.is_running = False
        
        # Performance tracking
        self.performance_metrics = {
            "total_collections": 0,
            "successful_collections": 0,
            "failed_collections": 0,
            "average_processing_time": 0.0,
            "data_quality_average": 0.0
        }
        
        # Initialize default collection jobs
        self._initialize_default_jobs()
    
    def _initialize_default_jobs(self):
        """Initialize default data collection jobs"""
        
        default_jobs = [
            # Real-time weather data collection
            CollectionJob(
                job_id="weather_realtime",
                job_name="Real-time Weather Data",
                data_type="current_weather",
                category=DataCategory.REALTIME_EXTERNAL,
                frequency=CollectionFrequency.HOURLY,
                source_type=DataSourceType.API_ENDPOINT,
                collection_parameters={
                    "include_forecast": True,
                    "weather_parameters": ["temperature", "humidity", "precipitation", "wind"]
                }
            ),
            
            # Daily market prices
            CollectionJob(
                job_id="market_prices_daily",
                job_name="Daily Market Prices",
                data_type="market_prices",
                category=DataCategory.REALTIME_EXTERNAL,
                frequency=CollectionFrequency.DAILY,
                source_type=DataSourceType.API_ENDPOINT,
                collection_parameters={
                    "commodities": ["wheat", "rice", "maize", "cotton", "sugarcane"],
                    "markets": ["national", "local"]
                }
            ),
            
            # Weekly satellite imagery
            CollectionJob(
                job_id="satellite_weekly",
                job_name="Weekly Satellite Analysis",
                data_type="satellite_imagery",
                category=DataCategory.REALTIME_EXTERNAL,
                frequency=CollectionFrequency.WEEKLY,
                source_type=DataSourceType.SATELLITE,
                collection_parameters={
                    "analysis_type": "ndvi",
                    "cloud_threshold": 20,
                    "resolution": "10m"
                }
            ),
            
            # Daily pest alerts
            CollectionJob(
                job_id="pest_alerts_daily",
                job_name="Daily Pest Alerts",
                data_type="pest_alerts",
                category=DataCategory.REALTIME_EXTERNAL,
                frequency=CollectionFrequency.DAILY,
                source_type=DataSourceType.API_ENDPOINT,
                collection_parameters={
                    "alert_levels": ["medium", "high", "critical"],
                    "crop_types": ["all"]
                }
            ),
            
            # Daily soil health monitoring (for farms with sensors)
            CollectionJob(
                job_id="soil_monitoring_daily",
                job_name="Daily Soil Health Monitoring",
                data_type="soil_health_analysis",
                category=DataCategory.HYBRID_COMPUTED,
                frequency=CollectionFrequency.DAILY,
                source_type=DataSourceType.IOT_SENSOR,
                collection_parameters={
                    "sensors": ["moisture", "temperature", "ph", "nutrients"],
                    "aggregation": "daily_average"
                }
            ),
            
            # Weekly rainfall pattern analysis
            CollectionJob(
                job_id="rainfall_analysis_weekly",
                job_name="Weekly Rainfall Pattern Analysis",
                data_type="rainfall_pattern_analysis",
                category=DataCategory.HYBRID_COMPUTED,
                frequency=CollectionFrequency.WEEKLY,
                source_type=DataSourceType.CALCULATED,
                collection_parameters={
                    "analysis_window_days": 7,
                    "include_predictions": True
                }
            ),
            
            # Monthly government schemes update
            CollectionJob(
                job_id="schemes_monthly",
                job_name="Monthly Government Schemes Update",
                data_type="government_schemes",
                category=DataCategory.REALTIME_EXTERNAL,
                frequency=CollectionFrequency.MONTHLY,
                source_type=DataSourceType.API_ENDPOINT,
                collection_parameters={
                    "scheme_categories": ["subsidy", "insurance", "loan", "training"]
                }
            ),
            
            # Seasonal crop recommendations
            CollectionJob(
                job_id="crop_recommendations_seasonal",
                job_name="Seasonal Crop Recommendations",
                data_type="crop_recommendation",
                category=DataCategory.HYBRID_COMPUTED,
                frequency=CollectionFrequency.SEASONAL,
                source_type=DataSourceType.CALCULATED,
                collection_parameters={
                    "recommendation_types": ["crop_selection", "planting_schedule", "input_optimization"]
                }
            )
        ]
        
        # Add all default jobs
        for job in default_jobs:
            self.collection_jobs[job.job_id] = job
            self._schedule_job(job)
        
        logger.info(f"Initialized {len(default_jobs)} default collection jobs")
    
    def _schedule_job(self, job: CollectionJob):
        """Schedule a collection job based on its frequency"""
        try:
            if job.frequency == CollectionFrequency.REAL_TIME:
                # Real-time jobs run every 5 minutes
                self.scheduler.every(5).minutes.do(self._run_collection_job, job.job_id)
            elif job.frequency == CollectionFrequency.HOURLY:
                self.scheduler.every().hour.do(self._run_collection_job, job.job_id)
            elif job.frequency == CollectionFrequency.DAILY:
                self.scheduler.every().day.at("06:00").do(self._run_collection_job, job.job_id)
            elif job.frequency == CollectionFrequency.WEEKLY:
                self.scheduler.every().monday.at("07:00").do(self._run_collection_job, job.job_id)
            elif job.frequency == CollectionFrequency.MONTHLY:
                self.scheduler.every().day.at("08:00").do(self._check_monthly_job, job.job_id)
            elif job.frequency == CollectionFrequency.SEASONAL:
                # Seasonal jobs are triggered manually based on calendar
                pass
            
            # Update next run time
            job.next_run = self._calculate_next_run_time(job)
            
            logger.info(f"Scheduled job {job.job_id} with frequency {job.frequency.value}")
            
        except Exception as e:
            logger.error(f"Error scheduling job {job.job_id}: {e}")
    
    def _calculate_next_run_time(self, job: CollectionJob) -> datetime:
        """Calculate next run time for a job"""
        now = datetime.utcnow()
        
        if job.frequency == CollectionFrequency.REAL_TIME:
            return now + timedelta(minutes=5)
        elif job.frequency == CollectionFrequency.HOURLY:
            return now + timedelta(hours=1)
        elif job.frequency == CollectionFrequency.DAILY:
            tomorrow = now.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
            return tomorrow
        elif job.frequency == CollectionFrequency.WEEKLY:
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            next_monday = now + timedelta(days=days_until_monday)
            return next_monday.replace(hour=7, minute=0, second=0, microsecond=0)
        elif job.frequency == CollectionFrequency.MONTHLY:
            next_month = now.replace(day=1, hour=8, minute=0, second=0, microsecond=0)
            if now.day > 1:
                next_month = next_month.replace(month=next_month.month + 1)
            return next_month
        else:
            return now + timedelta(days=1)  # Default to daily
    
    async def start_automated_collection(self):
        """Start the automated data collection system"""
        try:
            logger.info("Starting automated data collection system...")
            self.is_running = True
            
            # Initialize data coordinator if not already done
            if not self.data_coordinator.is_initialized:
                await self.data_coordinator.initialize()
            
            # Start the scheduler in a separate thread
            def run_scheduler():
                while self.is_running:
                    self.scheduler.run_pending()
                    time.sleep(1)
            
            self.executor.submit(run_scheduler)
            
            logger.info("Automated data collection system started successfully")
            
        except Exception as e:
            logger.error(f"Error starting automated collection: {e}")
            raise
    
    async def stop_automated_collection(self):
        """Stop the automated data collection system"""
        try:
            logger.info("Stopping automated data collection system...")
            self.is_running = False
            
            # Clear scheduled jobs
            self.scheduler.clear()
            
            # Shutdown executor
            self.executor.shutdown(wait=True)
            
            logger.info("Automated data collection system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping automated collection: {e}")
    
    def _run_collection_job(self, job_id: str):
        """Run a specific collection job"""
        if not self.is_running:
            return
        
        try:
            job = self.collection_jobs.get(job_id)
            if not job or not job.is_active:
                return
            
            logger.info(f"Running collection job: {job.job_name}")
            
            # Run the job asynchronously
            asyncio.create_task(self._execute_collection_job(job))
            
        except Exception as e:
            logger.error(f"Error running collection job {job_id}: {e}")
    
    async def _execute_collection_job(self, job: CollectionJob):
        """Execute a collection job for all target farmers"""
        start_time = datetime.utcnow()
        
        try:
            # Get target farmers
            target_farmers = await self._get_target_farmers(job)
            
            if not target_farmers:
                logger.warning(f"No target farmers found for job {job.job_id}")
                return
            
            # Collect data for each farmer
            collection_results = []
            
            for farmer_id in target_farmers:
                try:
                    result = await self._collect_data_for_farmer(job, farmer_id)
                    collection_results.append(result)
                    
                    # Store result in history
                    self.collection_history.append(result)
                    
                    # Update performance metrics
                    self.performance_metrics["total_collections"] += 1
                    if result.success:
                        self.performance_metrics["successful_collections"] += 1
                    else:
                        self.performance_metrics["failed_collections"] += 1
                    
                except Exception as e:
                    logger.error(f"Error collecting data for farmer {farmer_id} in job {job.job_id}: {e}")
                    
                    # Record failure
                    failure_result = CollectionResult(
                        job_id=job.job_id,
                        farmer_id=farmer_id,
                        success=False,
                        error_message=str(e)
                    )
                    collection_results.append(failure_result)
                    self.collection_history.append(failure_result)
                    self.performance_metrics["failed_collections"] += 1
            
            # Update job statistics
            successful_collections = sum(1 for r in collection_results if r.success)
            job.success_count += successful_collections
            job.failure_count += len(collection_results) - successful_collections
            job.last_run = datetime.utcnow()
            job.next_run = self._calculate_next_run_time(job)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Completed job {job.job_id}: {successful_collections}/{len(collection_results)} successful in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error executing collection job {job.job_id}: {e}")
            job.failure_count += 1
            job.last_run = datetime.utcnow()
    
    async def _get_target_farmers(self, job: CollectionJob) -> List[str]:
        """Get list of target farmers for a collection job"""
        try:
            if job.target_farmers:
                # Specific farmers targeted
                return job.target_farmers
            else:
                # All active farmers
                # This would typically query the database for active farmers
                # For now, return a sample list
                return ["FARM001", "FARM002", "FARM003"]  # Sample farmer IDs
                
        except Exception as e:
            logger.error(f"Error getting target farmers for job {job.job_id}: {e}")
            return []
    
    async def _collect_data_for_farmer(self, job: CollectionJob, farmer_id: str) -> CollectionResult:
        """Collect data for a specific farmer"""
        start_time = datetime.utcnow()
        
        try:
            # Get farmer location (this would come from database)
            farmer_location = await self._get_farmer_location(farmer_id)
            
            if not farmer_location:
                raise ValueError(f"No location found for farmer {farmer_id}")
            
            # Create data request
            request = DataRequest(
                request_id=str(uuid.uuid4()),
                category=job.category,
                data_type=job.data_type,
                location=farmer_location,
                farmer_id=farmer_id,
                parameters=job.collection_parameters,
                priority=DataPriority.MEDIUM
            )
            
            # Execute data collection
            response = await self.data_coordinator.process_data_request(request)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            if response.success:
                # Process and store the collected data
                await self._process_collected_data(farmer_id, job.data_type, response.data)
                
                result = CollectionResult(
                    job_id=job.job_id,
                    farmer_id=farmer_id,
                    success=True,
                    data_collected=response.data,
                    processing_time_seconds=processing_time,
                    data_quality_score=response.quality_score
                )
                
                logger.debug(f"Successfully collected {job.data_type} data for farmer {farmer_id}")
                return result
            else:
                result = CollectionResult(
                    job_id=job.job_id,
                    farmer_id=farmer_id,
                    success=False,
                    error_message=response.error,
                    processing_time_seconds=processing_time
                )
                
                logger.warning(f"Failed to collect {job.data_type} data for farmer {farmer_id}: {response.error}")
                return result
                
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            result = CollectionResult(
                job_id=job.job_id,
                farmer_id=farmer_id,
                success=False,
                error_message=str(e),
                processing_time_seconds=processing_time
            )
            
            logger.error(f"Exception collecting data for farmer {farmer_id}: {e}")
            return result
    
    async def _get_farmer_location(self, farmer_id: str) -> Optional[Dict[str, float]]:
        """Get farmer location from database"""
        try:
            # This would query the database for farmer location
            # For now, return sample locations
            sample_locations = {
                "FARM001": {"latitude": 28.6139, "longitude": 77.2090},  # Delhi
                "FARM002": {"latitude": 19.0760, "longitude": 72.8777},  # Mumbai
                "FARM003": {"latitude": 13.0827, "longitude": 80.2707}   # Chennai
            }
            
            return sample_locations.get(farmer_id, {"latitude": 28.6139, "longitude": 77.2090})
            
        except Exception as e:
            logger.error(f"Error getting farmer location for {farmer_id}: {e}")
            return None
    
    async def _process_collected_data(self, farmer_id: str, data_type: str, collected_data: Dict[str, Any]):
        """Process and store collected data"""
        try:
            # Store in database
            # await self.data_coordinator.db_manager.store_collected_data(farmer_id, data_type, collected_data)
            
            # Update farmer progress if applicable
            if data_type in ["soil_health_analysis", "crop_recommendation"]:
                await self.workflow_manager.update_farmer_progress(farmer_id, collected_data)
            
            # Trigger alerts or notifications if needed
            await self._check_for_alerts(farmer_id, data_type, collected_data)
            
            logger.debug(f"Processed collected data for farmer {farmer_id}, type {data_type}")
            
        except Exception as e:
            logger.error(f"Error processing collected data: {e}")
    
    async def _check_for_alerts(self, farmer_id: str, data_type: str, data: Dict[str, Any]):
        """Check if collected data triggers any alerts"""
        try:
            alerts_triggered = []
            
            # Weather alerts
            if data_type == "current_weather" and "weather_data" in data:
                weather = data["weather_data"]["data"]["current_conditions"]
                if weather.get("temperature", 0) > 40:
                    alerts_triggered.append("high_temperature_alert")
                if weather.get("wind_speed", 0) > 25:
                    alerts_triggered.append("high_wind_alert")
            
            # Soil health alerts
            elif data_type == "soil_health_analysis" and "soil_health" in data:
                soil_health = data["soil_health"]
                if soil_health.get("overall_score", 100) < 50:
                    alerts_triggered.append("poor_soil_health_alert")
            
            # Pest alerts
            elif data_type == "pest_alerts" and "pest_data" in data:
                pest_data = data["pest_data"]["data"]
                if pest_data.get("total_alerts", 0) > 0:
                    alerts_triggered.append("pest_detected_alert")
            
            # Send alerts (in real implementation, this would send notifications)
            if alerts_triggered:
                logger.info(f"Triggered alerts for farmer {farmer_id}: {alerts_triggered}")
            
        except Exception as e:
            logger.error(f"Error checking for alerts: {e}")
    
    def _check_monthly_job(self, job_id: str):
        """Check if a monthly job should run today"""
        try:
            job = self.collection_jobs.get(job_id)
            if not job:
                return
            
            today = datetime.utcnow().date()
            if today.day == 1:  # First day of month
                self._run_collection_job(job_id)
                
        except Exception as e:
            logger.error(f"Error checking monthly job {job_id}: {e}")
    
    def add_collection_job(self, job: CollectionJob):
        """Add a new collection job"""
        try:
            self.collection_jobs[job.job_id] = job
            self._schedule_job(job)
            logger.info(f"Added new collection job: {job.job_name}")
            
        except Exception as e:
            logger.error(f"Error adding collection job: {e}")
    
    def remove_collection_job(self, job_id: str):
        """Remove a collection job"""
        try:
            if job_id in self.collection_jobs:
                job = self.collection_jobs[job_id]
                job.is_active = False
                del self.collection_jobs[job_id]
                logger.info(f"Removed collection job: {job_id}")
            else:
                logger.warning(f"Collection job not found: {job_id}")
                
        except Exception as e:
            logger.error(f"Error removing collection job: {e}")
    
    def update_job_parameters(self, job_id: str, new_parameters: Dict[str, Any]):
        """Update parameters for an existing job"""
        try:
            if job_id in self.collection_jobs:
                job = self.collection_jobs[job_id]
                job.collection_parameters.update(new_parameters)
                logger.info(f"Updated parameters for job {job_id}")
            else:
                logger.warning(f"Collection job not found: {job_id}")
                
        except Exception as e:
            logger.error(f"Error updating job parameters: {e}")
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a collection job"""
        try:
            if job_id not in self.collection_jobs:
                return None
            
            job = self.collection_jobs[job_id]
            recent_results = [r for r in self.collection_history if r.job_id == job_id][-10:]
            
            status = {
                "job_id": job_id,
                "job_name": job.job_name,
                "is_active": job.is_active,
                "frequency": job.frequency.value,
                "last_run": job.last_run,
                "next_run": job.next_run,
                "success_count": job.success_count,
                "failure_count": job.failure_count,
                "success_rate": job.success_count / (job.success_count + job.failure_count) if (job.success_count + job.failure_count) > 0 else 0,
                "recent_results": len(recent_results),
                "recent_success_rate": sum(1 for r in recent_results if r.success) / len(recent_results) if recent_results else 0
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return None
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        try:
            active_jobs = sum(1 for job in self.collection_jobs.values() if job.is_active)
            total_jobs = len(self.collection_jobs)
            
            # Calculate performance metrics
            if self.performance_metrics["total_collections"] > 0:
                success_rate = (self.performance_metrics["successful_collections"] / 
                              self.performance_metrics["total_collections"]) * 100
            else:
                success_rate = 0
            
            # Recent activity (last 24 hours)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_collections = [r for r in self.collection_history if r.collection_timestamp > recent_cutoff]
            
            status = {
                "is_running": self.is_running,
                "total_jobs": total_jobs,
                "active_jobs": active_jobs,
                "inactive_jobs": total_jobs - active_jobs,
                "performance_metrics": self.performance_metrics,
                "success_rate_percentage": round(success_rate, 2),
                "recent_activity": {
                    "last_24h_collections": len(recent_collections),
                    "last_24h_success_rate": (sum(1 for r in recent_collections if r.success) / len(recent_collections) * 100) if recent_collections else 0
                },
                "system_health": "healthy" if success_rate > 80 else "warning" if success_rate > 60 else "critical",
                "status_timestamp": datetime.utcnow()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}
    
    async def trigger_manual_collection(self, job_id: str, farmer_ids: List[str] = None) -> Dict[str, Any]:
        """Manually trigger a collection job"""
        try:
            if job_id not in self.collection_jobs:
                return {"success": False, "error": f"Job {job_id} not found"}
            
            job = self.collection_jobs[job_id]
            
            # Override target farmers if specified
            original_targets = job.target_farmers.copy()
            if farmer_ids:
                job.target_farmers = farmer_ids
            
            # Execute the job
            await self._execute_collection_job(job)
            
            # Restore original targets
            job.target_farmers = original_targets
            
            return {
                "success": True,
                "job_id": job_id,
                "triggered_at": datetime.utcnow(),
                "target_farmers": farmer_ids or "all"
            }
            
        except Exception as e:
            logger.error(f"Error triggering manual collection: {e}")
            return {"success": False, "error": str(e)}
    
    def get_collection_history(self, job_id: str = None, farmer_id: str = None, 
                             hours: int = 24) -> List[CollectionResult]:
        """Get collection history filtered by parameters"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            filtered_results = []
            for result in self.collection_history:
                if result.collection_timestamp < cutoff_time:
                    continue
                    
                if job_id and result.job_id != job_id:
                    continue
                    
                if farmer_id and result.farmer_id != farmer_id:
                    continue
                
                filtered_results.append(result)
            
            # Sort by timestamp (most recent first)
            filtered_results.sort(key=lambda r: r.collection_timestamp, reverse=True)
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error getting collection history: {e}")
            return []

# Example usage
async def main():
    """Example usage of Automated Data Collector"""
    
    # Initialize dependencies (these would be properly initialized in main.py)
    data_coordinator = DataCoordinator()
    workflow_manager = ProgressiveWorkflowManager(data_coordinator)
    
    # Create automated collector
    collector = AutomatedDataCollector(data_coordinator, workflow_manager)
    
    try:
        # Start automated collection
        await collector.start_automated_collection()
        
        # Get system status
        status = collector.get_system_status()
        print(f"System Status: {status['system_health']}")
        print(f"Active Jobs: {status['active_jobs']}/{status['total_jobs']}")
        print(f"Success Rate: {status['success_rate_percentage']:.1f}%")
        
        # Manually trigger a collection job
        manual_result = await collector.trigger_manual_collection(
            "weather_realtime", 
            ["FARM001", "FARM002"]
        )
        print(f"Manual collection: {manual_result['success']}")
        
        # Get recent collection history
        recent_collections = collector.get_collection_history(hours=24)
        print(f"Recent collections: {len(recent_collections)}")
        
        # Let it run for a bit
        await asyncio.sleep(10)
        
    finally:
        # Stop the collector
        await collector.stop_automated_collection()

if __name__ == "__main__":
    asyncio.run(main())