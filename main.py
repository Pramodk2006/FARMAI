# STEP 7: Initialize and Run System

import asyncio
import logging
import os
import sys
import signal
from datetime import datetime
from typing import Dict, Any, Optional
import argparse
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
from src.database.mongodb_setup import MongoDBSetup

from src.database import mongodb_setup
from src.apis import realtime_fetchers
from src.hybrid import managers
from src.core import data_coordinator
from src.profiling import progressive_workflow
from src.automated import data_collector

import uvicorn

if __name__ == "__main__":
    try:
        # This avoids calling asyncio.run when event loop exists
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Import our custom modules
from src.database.mongodb_setup import MongoDBSetup
from src.apis.realtime_fetchers import RealTimeDataFetcher
from src.hybrid.managers import HybridDataManager
from src.core.data_coordinator import DataCoordinator, DataRequest, DataCategory, DataPriority
from src.profiling.progressive_workflow import ProgressiveWorkflowManager
from src.automated.data_collector import AutomatedDataCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agricultural_ai.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgriculturalAISystem:
    """
    Main Agricultural AI System Application
    Coordinates all subsystems and provides unified interface
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the Agricultural AI System
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_configuration(config_path)
        
        # Core components
        self.db_manager: Optional[MongoDBSetup] = None
        self.data_coordinator: Optional[DataCoordinator] = None
        self.workflow_manager: Optional[ProgressiveWorkflowManager] = None
        self.data_collector: Optional[AutomatedDataCollector] = None
        
        # FastAPI application
        self.app = FastAPI(
            title="Agricultural AI System",
            description="Comprehensive AI system for agricultural data management and insights",
            version="1.0.0"
        )
        
        # System state
        self.is_initialized = False
        self.is_running = False
        
        # Setup FastAPI
        self._setup_fastapi()
    
    def _load_configuration(self, config_path: str = None) -> Dict[str, Any]:
        """Load system configuration"""
        try:
            # Default configuration
            default_config = {
                "database": {
                    "mongodb_uri": os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
                    "database_name": "agricultural_ai"
                },
                "apis": {
                    "weather_api_key": os.getenv("WEATHER_API_KEY", ""),
                    "market_api_key": os.getenv("MARKET_API_KEY", ""),
                    "satellite_api_key": os.getenv("SATELLITE_API_KEY", ""),
                    "pest_api_key": os.getenv("PEST_API_KEY", ""),
                    "schemes_api_key": os.getenv("SCHEMES_API_KEY", "")
                },
                "system": {
                    "debug_mode": os.getenv("DEBUG", "false").lower() == "true",
                    "log_level": "INFO",
                    "max_workers": 5,
                    "cache_ttl_minutes": 60
                },
                "server": {
                    "host": "0.0.0.0",
                    "port": 8000,
                    "reload": False
                }
            }
            
            # Load from file if provided
            if config_path and os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
                logger.info(f"Loaded configuration from {config_path}")
            else:
                logger.info("Using default configuration with environment variables")
            
            return default_config
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def _setup_fastapi(self):
        """Setup FastAPI application with routes and middleware"""
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Health check endpoint
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy" if self.is_running else "initializing",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "components": {
                    "database": self.db_manager is not None,
                    "data_coordinator": self.data_coordinator is not None,
                    "workflow_manager": self.workflow_manager is not None,
                    "data_collector": self.data_collector is not None
                }
            }
        
        # System status endpoint
        @self.app.get("/api/system/status")
        async def get_system_status():
            if not self.is_running:
                raise HTTPException(status_code=503, detail="System not running")
            
            try:
                # Get performance report from data coordinator
                coordinator_report = await self.data_coordinator.get_performance_report()
                
                # Get data collector status
                collector_status = self.data_collector.get_system_status()
                
                return {
                    "system_status": "running",
                    "data_coordinator": coordinator_report,
                    "data_collector": collector_status,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error getting system status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Farmer data endpoint
        @self.app.get("/api/farmers/{farmer_id}/comprehensive-data")
        async def get_farmer_comprehensive_data(farmer_id: str, 
                                              latitude: float = None, 
                                              longitude: float = None):
            if not self.is_running:
                raise HTTPException(status_code=503, detail="System not running")
            
            try:
                # Use provided coordinates or get from database
                if latitude is not None and longitude is not None:
                    location = {"latitude": latitude, "longitude": longitude}
                else:
                    # Get farmer location from database
                    farmer_profile = await self.db_manager.get_farmer_profile(farmer_id)
                    if not farmer_profile or "location" not in farmer_profile:
                        raise HTTPException(status_code=404, detail="Farmer location not found")
                    location = {
                        "latitude": farmer_profile["location"]["coordinates"]["latitude"],
                        "longitude": farmer_profile["location"]["coordinates"]["longitude"]
                    }
                
                # Get comprehensive data
                comprehensive_data = await self.data_coordinator.get_comprehensive_farmer_data(
                    farmer_id, location
                )
                
                return comprehensive_data
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting comprehensive farmer data: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Progressive profiling endpoint
        @self.app.post("/api/farmers/{farmer_id}/workflow-step")
        async def execute_workflow_step(farmer_id: str, step_data: dict):
            if not self.is_running:
                raise HTTPException(status_code=503, detail="System not running")
            
            try:
                step_id = step_data.get("step_id")
                collected_data = step_data.get("data", {})
                
                if not step_id:
                    raise HTTPException(status_code=400, detail="step_id is required")
                
                result = await self.workflow_manager.execute_workflow_step(
                    farmer_id, step_id, collected_data
                )
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error executing workflow step: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Get next workflow steps
        @self.app.get("/api/farmers/{farmer_id}/next-steps")
        async def get_next_workflow_steps(farmer_id: str, max_steps: int = 3):
            if not self.is_running:
                raise HTTPException(status_code=503, detail="System not running")
            
            try:
                next_steps = await self.workflow_manager.get_next_workflow_steps(
                    farmer_id, max_steps
                )
                
                return {
                    "farmer_id": farmer_id,
                    "next_steps": [step.__dict__ for step in next_steps],
                    "count": len(next_steps)
                }
                
            except Exception as e:
                logger.error(f"Error getting next workflow steps: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Data collection management endpoints
        @self.app.get("/api/data-collection/jobs")
        async def get_collection_jobs():
            if not self.is_running:
                raise HTTPException(status_code=503, detail="System not running")
            
            try:
                jobs_status = {}
                for job_id in self.data_collector.collection_jobs.keys():
                    jobs_status[job_id] = self.data_collector.get_job_status(job_id)
                
                return {"jobs": jobs_status}
                
            except Exception as e:
                logger.error(f"Error getting collection jobs: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/data-collection/jobs/{job_id}/trigger")
        async def trigger_collection_job(job_id: str, request_data: dict = None):
            if not self.is_running:
                raise HTTPException(status_code=503, detail="System not running")
            
            try:
                farmer_ids = request_data.get("farmer_ids", []) if request_data else []
                
                result = await self.data_collector.trigger_manual_collection(
                    job_id, farmer_ids
                )
                
                if result["success"]:
                    return result
                else:
                    raise HTTPException(status_code=400, detail=result["error"])
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error triggering collection job: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Real-time data request endpoint
        @self.app.post("/api/data/request")
        async def request_data(request_data: dict):
            if not self.is_running:
                raise HTTPException(status_code=503, detail="System not running")
            
            try:
                # Create data request
                request = DataRequest(
                    request_id=request_data.get("request_id", f"req_{datetime.utcnow().timestamp()}"),
                    category=DataCategory(request_data["category"]),
                    data_type=request_data["data_type"],
                    location=request_data["location"],
                    farmer_id=request_data.get("farmer_id"),
                    parameters=request_data.get("parameters", {}),
                    priority=DataPriority(request_data.get("priority", "medium"))
                )
                
                # Process request
                response = await self.data_coordinator.process_data_request(request)
                
                return {
                    "request_id": response.request_id,
                    "success": response.success,
                    "data": response.data,
                    "error": response.error,
                    "processing_time": response.processing_time,
                    "data_sources": response.data_sources,
                    "quality_score": response.quality_score,
                    "timestamp": response.timestamp.isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error processing data request: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def initialize(self):
        """Initialize all system components"""
        try:
            logger.info("Initializing Agricultural AI System...")
            
            # Initialize database manager
            self.db_manager = MongoDBSetup(
                uri=self.config["database"]["mongodb_uri"],
                db_name=self.config["database"]["database_name"]
            )
            await self.db_manager.connect()
            logger.info("Database manager initialized")
            
            # Initialize data coordinator
            self.data_coordinator = DataCoordinator(config=self.config)
            await self.data_coordinator.initialize()
            logger.info("Data coordinator initialized")
            
            # Initialize workflow manager
            self.workflow_manager = ProgressiveWorkflowManager(self.data_coordinator)
            logger.info("Workflow manager initialized")
            
            # Initialize data collector
            self.data_collector = AutomatedDataCollector(
                self.data_coordinator, 
                self.workflow_manager
            )
            logger.info("Data collector initialized")
            
            self.is_initialized = True
            logger.info("Agricultural AI System initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Error initializing system: {e}")
            raise
    
    async def start(self):
        """Start the Agricultural AI System"""
        try:
            if not self.is_initialized:
                await self.initialize()
            
            logger.info("Starting Agricultural AI System...")
            
            # Start automated data collection
            await self.data_collector.start_automated_collection()
            
            self.is_running = True
            logger.info("Agricultural AI System started successfully")
            
        except Exception as e:
            logger.error(f"Error starting system: {e}")
            raise
    
    async def stop(self):
        """Stop the Agricultural AI System"""
        try:
            logger.info("Stopping Agricultural AI System...")
            
            self.is_running = False
            
            # Stop data collector
            if self.data_collector:
                await self.data_collector.stop_automated_collection()
            
            # Cleanup resources
            if self.data_coordinator:
                await self.data_coordinator.cleanup_resources()
            
            logger.info("Agricultural AI System stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping system: {e}")
    
    def run_server(self):
        """Run the FastAPI server"""
        try:
            logger.info("Starting FastAPI server...")
            
            uvicorn.run(
                self.app,
                host=self.config["server"]["host"],
                port=self.config["server"]["port"],
                reload=self.config["server"]["reload"],
                access_log=True
            )
            
        except Exception as e:
            logger.error(f"Error running server: {e}")
            raise

# Global system instance
agricultural_system: Optional[AgriculturalAISystem] = None

def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    if agricultural_system:
        asyncio.create_task(agricultural_system.stop())
    sys.exit(0)

async def main():
    """Main application entry point"""
    global agricultural_system
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Agricultural AI System")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--mode", choices=["server", "worker", "both"], 
                       default="both", help="Run mode")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    
    args = parser.parse_args()
    
    try:
        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create system instance
        agricultural_system = AgriculturalAISystem(config_path=args.config)
        
        # Override server config if provided
        if args.host:
            agricultural_system.config["server"]["host"] = args.host
        if args.port:
            agricultural_system.config["server"]["port"] = args.port
        
        # Start system based on mode
        if args.mode in ["worker", "both"]:
            await agricultural_system.start()
        
        if args.mode in ["server", "both"]:
            # Run server (this blocks)
            agricultural_system.run_server()
        elif args.mode == "worker":
            # Keep worker running
            logger.info("Agricultural AI System worker running. Press Ctrl+C to stop.")
            while agricultural_system.is_running:
                await asyncio.sleep(1)
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
    finally:
        if agricultural_system:
            await agricultural_system.stop()

def run_development_server():
    """Run development server with hot reload"""
    import uvicorn
    
    # Create a simple FastAPI app for development
    agricultural_system = AgriculturalAISystem()
    
    # Initialize system in startup event
    @agricultural_system.app.on_event("startup")
    async def startup_event():
        await agricultural_system.start()
    
    @agricultural_system.app.on_event("shutdown")
    async def shutdown_event():
        await agricultural_system.stop()
    
    # Run with uvicorn
    uvicorn.run(
        agricultural_system.app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["src/"]
    )

if __name__ == "__main__":
    # Check if running in development mode
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        run_development_server()
    else:
        asyncio.run(main())# Create a global instance of the system
agricultural_system = AgriculturalAISystem()

# Expose FastAPI app globally for Uvicorn
app = agricultural_system.app
