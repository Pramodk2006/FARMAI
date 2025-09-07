# STEP 5: Progressive Workflow and Profiling

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from collections import defaultdict

# Import our custom modules
from src.core.data_coordinator import DataCoordinator, DataRequest, DataCategory, DataPriority

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProfileCompletionLevel(Enum):
    """Profile completion levels"""
    BASIC = "basic"           # 0-25% complete
    INTERMEDIATE = "intermediate"  # 26-60% complete
    ADVANCED = "advanced"     # 61-85% complete
    COMPREHENSIVE = "comprehensive"  # 86-100% complete

class DataCollectionStage(Enum):
    """Data collection stages in progressive profiling"""
    REGISTRATION = "registration"
    BASIC_PROFILING = "basic_profiling"
    FARM_DETAILS = "farm_details"
    CROP_HISTORY = "crop_history"
    PREFERENCES = "preferences"
    ADVANCED_ANALYTICS = "advanced_analytics"
    CONTINUOUS_MONITORING = "continuous_monitoring"

@dataclass
class ProfileProgress:
    """Track farmer profile progress"""
    farmer_id: str
    current_stage: DataCollectionStage
    completion_percentage: float
    completion_level: ProfileCompletionLevel
    completed_stages: List[DataCollectionStage] = field(default_factory=list)
    pending_actions: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    next_scheduled_update: Optional[datetime] = None

@dataclass
class WorkflowStep:
    """Individual workflow step definition"""
    step_id: str
    step_name: str
    description: str
    stage: DataCollectionStage
    required_fields: List[str]
    optional_fields: List[str]
    dependencies: List[str] = field(default_factory=list)  # Other step_ids
    estimated_time_minutes: int = 5
    priority: int = 1  # 1-5, higher is more important
    is_recurring: bool = False
    recurrence_days: Optional[int] = None

class ProgressiveWorkflowManager:
    """
    Manages progressive profiling workflow for farmers
    Gradually collects data over time to reduce friction and improve data quality
    """
    
    def __init__(self, data_coordinator: DataCoordinator):
        """
        Initialize progressive workflow manager
        
        Args:
            data_coordinator: Data coordinator instance
        """
        self.data_coordinator = data_coordinator
        self.workflow_definitions = {}
        self.farmer_progress = {}  # farmer_id -> ProfileProgress
        self.workflow_templates = {}
        
        # Initialize workflow definitions
        self._initialize_workflow_definitions()
    
    def _initialize_workflow_definitions(self):
        """Initialize predefined workflow definitions"""
        
        # Registration stage workflow
        registration_steps = [
            WorkflowStep(
                step_id="basic_info",
                step_name="Basic Information",
                description="Collect farmer's basic personal information",
                stage=DataCollectionStage.REGISTRATION,
                required_fields=["farmer_name", "phone_number", "village", "district", "state"],
                optional_fields=["email", "age", "education_level"],
                estimated_time_minutes=3,
                priority=5
            ),
            WorkflowStep(
                step_id="consent",
                step_name="Data Consent",
                description="Obtain consent for data collection and usage",
                stage=DataCollectionStage.REGISTRATION,
                required_fields=["data_consent", "privacy_policy_accepted"],
                optional_fields=["marketing_consent", "research_consent"],
                dependencies=["basic_info"],
                estimated_time_minutes=2,
                priority=5
            )
        ]
        
        # Basic profiling stage
        basic_profiling_steps = [
            WorkflowStep(
                step_id="farming_experience",
                step_name="Farming Experience",
                description="Collect information about farming background",
                stage=DataCollectionStage.BASIC_PROFILING,
                required_fields=["years_of_experience", "primary_occupation"],
                optional_fields=["farming_methods", "training_received"],
                dependencies=["consent"],
                estimated_time_minutes=3,
                priority=4
            ),
            WorkflowStep(
                step_id="communication_preferences",
                step_name="Communication Preferences",
                description="Set up communication channels and language preferences",
                stage=DataCollectionStage.BASIC_PROFILING,
                required_fields=["preferred_language", "contact_method"],
                optional_fields=["notification_times", "frequency_preference"],
                dependencies=["farming_experience"],
                estimated_time_minutes=2,
                priority=3
            )
        ]
        
        # Farm details stage
        farm_details_steps = [
            WorkflowStep(
                step_id="land_details",
                step_name="Land Information",
                description="Collect details about farming land",
                stage=DataCollectionStage.FARM_DETAILS,
                required_fields=["total_land_area", "ownership_type", "soil_type"],
                optional_fields=["irrigation_source", "land_slope", "gps_coordinates"],
                dependencies=["communication_preferences"],
                estimated_time_minutes=5,
                priority=4
            ),
            WorkflowStep(
                step_id="infrastructure",
                step_name="Farm Infrastructure",
                description="Document available farm infrastructure",
                stage=DataCollectionStage.FARM_DETAILS,
                required_fields=["water_source", "storage_facilities"],
                optional_fields=["machinery_owned", "greenhouse_area", "livestock_count"],
                dependencies=["land_details"],
                estimated_time_minutes=4,
                priority=3
            )
        ]
        
        # Crop history stage
        crop_history_steps = [
            WorkflowStep(
                step_id="current_crops",
                step_name="Current Season Crops",
                description="Information about currently grown crops",
                stage=DataCollectionStage.CROP_HISTORY,
                required_fields=["crop_types", "planting_dates", "expected_harvest"],
                optional_fields=["seed_varieties", "fertilizers_used", "pest_issues"],
                dependencies=["infrastructure"],
                estimated_time_minutes=6,
                priority=4
            ),
            WorkflowStep(
                step_id="historical_yields",
                step_name="Historical Crop Data",
                description="Past 2-3 years of crop and yield data",
                stage=DataCollectionStage.CROP_HISTORY,
                required_fields=["previous_crops", "yield_data"],
                optional_fields=["market_prices", "storage_losses", "income_data"],
                dependencies=["current_crops"],
                estimated_time_minutes=8,
                priority=3
            )
        ]
        
        # Preferences stage
        preferences_steps = [
            WorkflowStep(
                step_id="advisory_preferences",
                step_name="Advisory Preferences",
                description="Customize advisory and recommendation preferences",
                stage=DataCollectionStage.PREFERENCES,
                required_fields=["advisory_topics", "alert_preferences"],
                optional_fields=["learning_style", "preferred_formats"],
                dependencies=["historical_yields"],
                estimated_time_minutes=4,
                priority=2
            ),
            WorkflowStep(
                step_id="market_interests",
                step_name="Market Interests",
                description="Market and selling preferences",
                stage=DataCollectionStage.PREFERENCES,
                required_fields=["selling_channels", "price_alert_crops"],
                optional_fields=["quality_standards", "certification_interest"],
                dependencies=["advisory_preferences"],
                estimated_time_minutes=3,
                priority=2
            )
        ]
        
        # Advanced analytics stage
        advanced_steps = [
            WorkflowStep(
                step_id="detailed_soil_data",
                step_name="Soil Analysis Integration",
                description="Integrate detailed soil test results",
                stage=DataCollectionStage.ADVANCED_ANALYTICS,
                required_fields=["soil_test_results", "nutrient_levels"],
                optional_fields=["organic_matter", "micronutrients", "soil_health_score"],
                dependencies=["market_interests"],
                estimated_time_minutes=10,
                priority=3
            ),
            WorkflowStep(
                step_id="weather_integration",
                step_name="Weather Data Integration",
                description="Set up personalized weather monitoring",
                stage=DataCollectionStage.ADVANCED_ANALYTICS,
                required_fields=["weather_station_preference", "critical_weather_alerts"],
                optional_fields=["microclimate_data", "irrigation_automation"],
                dependencies=["detailed_soil_data"],
                estimated_time_minutes=6,
                priority=2
            )
        ]
        
        # Continuous monitoring stage
        monitoring_steps = [
            WorkflowStep(
                step_id="sensor_integration",
                step_name="IoT Sensor Setup",
                description="Integrate IoT sensors for continuous monitoring",
                stage=DataCollectionStage.CONTINUOUS_MONITORING,
                required_fields=["sensor_types", "monitoring_parameters"],
                optional_fields=["automation_preferences", "alert_thresholds"],
                dependencies=["weather_integration"],
                estimated_time_minutes=15,
                priority=1,
                is_recurring=True,
                recurrence_days=30
            ),
            WorkflowStep(
                step_id="feedback_optimization",
                step_name="Continuous Improvement",
                description="Regular feedback and system optimization",
                stage=DataCollectionStage.CONTINUOUS_MONITORING,
                required_fields=["satisfaction_rating", "improvement_suggestions"],
                optional_fields=["feature_requests", "training_needs"],
                dependencies=["sensor_integration"],
                estimated_time_minutes=5,
                priority=2,
                is_recurring=True,
                recurrence_days=90
            )
        ]
        
        # Combine all steps into workflow definitions
        all_steps = (registration_steps + basic_profiling_steps + farm_details_steps + 
                    crop_history_steps + preferences_steps + advanced_steps + monitoring_steps)
        
        for step in all_steps:
            self.workflow_definitions[step.step_id] = step
        
        # Create stage-wise templates
        for stage in DataCollectionStage:
            stage_steps = [step for step in all_steps if step.stage == stage]
            self.workflow_templates[stage] = stage_steps
        
        logger.info(f"Initialized {len(all_steps)} workflow steps across {len(DataCollectionStage)} stages")
    
    async def initialize_farmer_profile(self, farmer_id: str, initial_data: Dict[str, Any]) -> ProfileProgress:
        """
        Initialize progressive profiling for a new farmer
        
        Args:
            farmer_id: Unique farmer identifier
            initial_data: Initial data collected during registration
            
        Returns:
            ProfileProgress object
        """
        try:
            # Create initial profile progress
            progress = ProfileProgress(
                farmer_id=farmer_id,
                current_stage=DataCollectionStage.REGISTRATION,
                completion_percentage=0.0,
                completion_level=ProfileCompletionLevel.BASIC
            )
            
            # Process initial data and determine completed steps
            completed_steps = self._analyze_completed_steps(initial_data)
            progress.completed_stages = list(set(step.stage for step in completed_steps))
            
            # Calculate initial completion percentage
            progress.completion_percentage = self._calculate_completion_percentage(completed_steps)
            progress.completion_level = self._determine_completion_level(progress.completion_percentage)
            
            # Determine next actions
            progress.pending_actions = await self._get_next_recommended_actions(farmer_id, completed_steps)
            
            # Schedule next update
            progress.next_scheduled_update = self._calculate_next_update_time(progress.current_stage)
            
            # Store progress
            self.farmer_progress[farmer_id] = progress
            
            logger.info(f"Initialized farmer profile for {farmer_id} at {progress.completion_percentage:.1f}% completion")
            return progress
            
        except Exception as e:
            logger.error(f"Error initializing farmer profile: {e}")
            raise
    
    async def update_farmer_progress(self, farmer_id: str, new_data: Dict[str, Any]) -> ProfileProgress:
        """
        Update farmer progress based on new data collected
        
        Args:
            farmer_id: Farmer identifier
            new_data: Newly collected data
            
        Returns:
            Updated ProfileProgress
        """
        try:
            # Get current progress or create new one
            if farmer_id in self.farmer_progress:
                progress = self.farmer_progress[farmer_id]
            else:
                progress = await self.initialize_farmer_profile(farmer_id, new_data)
                return progress
            
            # Analyze what steps are now completed with new data
            all_farmer_data = await self._get_all_farmer_data(farmer_id)
            all_farmer_data.update(new_data)  # Merge new data
            
            completed_steps = self._analyze_completed_steps(all_farmer_data)
            
            # Update progress
            old_completion = progress.completion_percentage
            progress.completion_percentage = self._calculate_completion_percentage(completed_steps)
            progress.completion_level = self._determine_completion_level(progress.completion_percentage)
            progress.completed_stages = list(set(step.stage for step in completed_steps))
            progress.current_stage = self._determine_current_stage(completed_steps)
            progress.last_updated = datetime.utcnow()
            
            # Update pending actions
            progress.pending_actions = await self._get_next_recommended_actions(farmer_id, completed_steps)
            
            # Schedule next update
            progress.next_scheduled_update = self._calculate_next_update_time(progress.current_stage)
            
            # Store updated progress
            self.farmer_progress[farmer_id] = progress
            
            improvement = progress.completion_percentage - old_completion
            logger.info(f"Updated farmer {farmer_id}: {old_completion:.1f}% -> {progress.completion_percentage:.1f}% (+{improvement:.1f}%)")
            
            return progress
            
        except Exception as e:
            logger.error(f"Error updating farmer progress: {e}")
            raise
    
    async def get_next_workflow_steps(self, farmer_id: str, max_steps: int = 3) -> List[WorkflowStep]:
        """
        Get next recommended workflow steps for farmer
        
        Args:
            farmer_id: Farmer identifier
            max_steps: Maximum number of steps to return
            
        Returns:
            List of recommended workflow steps
        """
        try:
            # Get current progress
            if farmer_id not in self.farmer_progress:
                logger.warning(f"No progress found for farmer {farmer_id}")
                return []
            
            progress = self.farmer_progress[farmer_id]
            
            # Get all farmer data to check completed steps
            all_farmer_data = await self._get_all_farmer_data(farmer_id)
            completed_steps = self._analyze_completed_steps(all_farmer_data)
            completed_step_ids = [step.step_id for step in completed_steps]
            
            # Find available next steps
            available_steps = []
            
            for step_id, step in self.workflow_definitions.items():
                # Skip if already completed
                if step_id in completed_step_ids:
                    continue
                
                # Check if dependencies are met
                if all(dep in completed_step_ids for dep in step.dependencies):
                    available_steps.append(step)
            
            # Sort by priority and stage progression
            available_steps.sort(key=lambda s: (-s.priority, s.stage.value))
            
            # Return top steps
            recommended_steps = available_steps[:max_steps]
            
            logger.info(f"Found {len(recommended_steps)} recommended steps for farmer {farmer_id}")
            return recommended_steps
            
        except Exception as e:
            logger.error(f"Error getting next workflow steps: {e}")
            raise
    
    async def execute_workflow_step(self, farmer_id: str, step_id: str, 
                                  collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a specific workflow step with collected data
        
        Args:
            farmer_id: Farmer identifier
            step_id: Workflow step identifier
            collected_data: Data collected for this step
            
        Returns:
            Execution result with validation and next steps
        """
        try:
            # Validate step exists
            if step_id not in self.workflow_definitions:
                raise ValueError(f"Unknown workflow step: {step_id}")
            
            step = self.workflow_definitions[step_id]
            
            # Validate collected data
            validation_result = self._validate_step_data(step, collected_data)
            
            if not validation_result["is_valid"]:
                return {
                    "success": False,
                    "errors": validation_result["errors"],
                    "missing_fields": validation_result["missing_fields"]
                }
            
            # Store the collected data
            await self._store_step_data(farmer_id, step_id, collected_data)
            
            # Update farmer progress
            updated_progress = await self.update_farmer_progress(farmer_id, collected_data)
            
            # Get next recommended steps
            next_steps = await self.get_next_workflow_steps(farmer_id, 3)
            
            # Trigger any automated actions based on completed step
            await self._trigger_post_step_actions(farmer_id, step, collected_data)
            
            execution_result = {
                "success": True,
                "step_completed": step_id,
                "farmer_progress": updated_progress.__dict__,
                "next_recommended_steps": [s.__dict__ for s in next_steps],
                "completion_improvement": validation_result.get("completion_boost", 0),
                "execution_timestamp": datetime.utcnow()
            }
            
            logger.info(f"Successfully executed step {step_id} for farmer {farmer_id}")
            return execution_result
            
        except Exception as e:
            logger.error(f"Error executing workflow step {step_id}: {e}")
            raise
    
    async def generate_personalized_workflow(self, farmer_id: str, 
                                           context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a personalized workflow plan for farmer
        
        Args:
            farmer_id: Farmer identifier
            context: Additional context for personalization
            
        Returns:
            Personalized workflow plan
        """
        try:
            context = context or {}
            
            # Get current progress
            if farmer_id in self.farmer_progress:
                progress = self.farmer_progress[farmer_id]
            else:
                # Initialize with basic data
                progress = await self.initialize_farmer_profile(farmer_id, {})
            
            # Get farmer context data
            farmer_data = await self._get_all_farmer_data(farmer_id)
            
            # Generate personalized plan
            workflow_plan = {
                "farmer_id": farmer_id,
                "current_progress": progress.__dict__,
                "personalization_factors": self._analyze_personalization_factors(farmer_data, context),
                "recommended_workflow": [],
                "estimated_completion_time": 0,
                "priority_adjustments": {},
                "generated_at": datetime.utcnow()
            }
            
            # Get next steps
            next_steps = await self.get_next_workflow_steps(farmer_id, 10)
            
            # Personalize step priorities and content
            for step in next_steps:
                personalized_step = self._personalize_workflow_step(step, farmer_data, context)
                workflow_plan["recommended_workflow"].append(personalized_step)
                workflow_plan["estimated_completion_time"] += personalized_step.get("estimated_time_minutes", 5)
            
            # Add contextual recommendations
            workflow_plan["contextual_recommendations"] = self._generate_contextual_recommendations(
                farmer_data, context, progress
            )
            
            logger.info(f"Generated personalized workflow for farmer {farmer_id} with {len(next_steps)} steps")
            return workflow_plan
            
        except Exception as e:
            logger.error(f"Error generating personalized workflow: {e}")
            raise
    
    async def get_farmer_analytics(self, farmer_id: str) -> Dict[str, Any]:
        """
        Get comprehensive analytics for farmer's profiling journey
        
        Args:
            farmer_id: Farmer identifier
            
        Returns:
            Analytics data
        """
        try:
            if farmer_id not in self.farmer_progress:
                return {"error": "Farmer not found in system"}
            
            progress = self.farmer_progress[farmer_id]
            farmer_data = await self._get_all_farmer_data(farmer_id)
            
            # Calculate various metrics
            analytics = {
                "farmer_id": farmer_id,
                "profile_completion": {
                    "percentage": progress.completion_percentage,
                    "level": progress.completion_level.value,
                    "completed_stages": [stage.value for stage in progress.completed_stages]
                },
                "engagement_metrics": self._calculate_engagement_metrics(farmer_id),
                "data_quality": self._assess_data_quality(farmer_data),
                "journey_timeline": self._generate_journey_timeline(farmer_id),
                "recommendations_impact": self._assess_recommendations_impact(farmer_id),
                "next_milestones": self._identify_next_milestones(progress),
                "generated_at": datetime.utcnow()
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error generating farmer analytics: {e}")
            raise
    
    def _analyze_completed_steps(self, farmer_data: Dict[str, Any]) -> List[WorkflowStep]:
        """Analyze which workflow steps are completed based on available data"""
        completed_steps = []
        
        for step_id, step in self.workflow_definitions.items():
            # Check if all required fields are present
            required_fields_present = all(
                field in farmer_data and farmer_data[field] is not None 
                for field in step.required_fields
            )
            
            if required_fields_present:
                completed_steps.append(step)
        
        return completed_steps
    
    def _calculate_completion_percentage(self, completed_steps: List[WorkflowStep]) -> float:
        """Calculate profile completion percentage"""
        total_steps = len(self.workflow_definitions)
        completed_count = len(completed_steps)
        
        if total_steps == 0:
            return 0.0
        
        return (completed_count / total_steps) * 100.0
    
    def _determine_completion_level(self, completion_percentage: float) -> ProfileCompletionLevel:
        """Determine completion level based on percentage"""
        if completion_percentage >= 86:
            return ProfileCompletionLevel.COMPREHENSIVE
        elif completion_percentage >= 61:
            return ProfileCompletionLevel.ADVANCED
        elif completion_percentage >= 26:
            return ProfileCompletionLevel.INTERMEDIATE
        else:
            return ProfileCompletionLevel.BASIC
    
    def _determine_current_stage(self, completed_steps: List[WorkflowStep]) -> DataCollectionStage:
        """Determine current stage based on completed steps"""
        if not completed_steps:
            return DataCollectionStage.REGISTRATION
        
        # Get all completed stages
        completed_stages = list(set(step.stage for step in completed_steps))
        
        # Find the most advanced completed stage
        stage_order = list(DataCollectionStage)
        max_stage_index = max(stage_order.index(stage) for stage in completed_stages)
        
        # If all steps in current stage are completed, move to next
        current_stage = stage_order[max_stage_index]
        current_stage_steps = [step for step in self.workflow_definitions.values() if step.stage == current_stage]
        completed_current_stage_steps = [step for step in completed_steps if step.stage == current_stage]
        
        if len(completed_current_stage_steps) == len(current_stage_steps):
            # All steps in current stage completed, move to next if available
            if max_stage_index + 1 < len(stage_order):
                return stage_order[max_stage_index + 1]
        
        return current_stage
    
    async def _get_next_recommended_actions(self, farmer_id: str, completed_steps: List[WorkflowStep]) -> List[str]:
        """Generate list of next recommended actions"""
        actions = []
        completed_step_ids = [step.step_id for step in completed_steps]
        
        # Find next available steps
        available_steps = []
        for step_id, step in self.workflow_definitions.items():
            if step_id not in completed_step_ids:
                if all(dep in completed_step_ids for dep in step.dependencies):
                    available_steps.append(step)
        
        # Convert to action descriptions
        for step in sorted(available_steps, key=lambda s: -s.priority)[:3]:
            actions.append(f"Complete {step.step_name}: {step.description}")
        
        if not actions:
            actions.append("Profile is complete. Continue with regular monitoring.")
        
        return actions
    
    def _calculate_next_update_time(self, current_stage: DataCollectionStage) -> datetime:
        """Calculate when the next profile update should occur"""
        # Different update frequencies based on stage
        update_intervals = {
            DataCollectionStage.REGISTRATION: 1,  # 1 day
            DataCollectionStage.BASIC_PROFILING: 3,  # 3 days
            DataCollectionStage.FARM_DETAILS: 7,  # 1 week
            DataCollectionStage.CROP_HISTORY: 14,  # 2 weeks
            DataCollectionStage.PREFERENCES: 30,  # 1 month
            DataCollectionStage.ADVANCED_ANALYTICS: 60,  # 2 months
            DataCollectionStage.CONTINUOUS_MONITORING: 90  # 3 months
        }
        
        days_until_next = update_intervals.get(current_stage, 7)
        return datetime.utcnow() + timedelta(days=days_until_next)
    
    async def _get_all_farmer_data(self, farmer_id: str) -> Dict[str, Any]:
        """Get all available data for a farmer"""
        try:
            # This would typically fetch from database
            # For now, return a placeholder that would be replaced with actual data retrieval
            farmer_data = {
                "farmer_id": farmer_id,
                "last_accessed": datetime.utcnow()
            }
            
            # In a real implementation, you would fetch from:
            # - MongoDB farmer profiles
            # - Recent data collection sessions
            # - Cached progressive profiling data
            
            return farmer_data
            
        except Exception as e:
            logger.error(f"Error getting farmer data: {e}")
            return {}
    
    def _validate_step_data(self, step: WorkflowStep, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data collected for a workflow step"""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "missing_fields": [],
            "completion_boost": 0
        }
        
        # Check required fields
        for field in step.required_fields:
            if field not in collected_data or collected_data[field] is None:
                validation_result["missing_fields"].append(field)
                validation_result["is_valid"] = False
        
        # Add field-specific validation rules
        validation_rules = {
            "phone_number": lambda x: len(str(x)) >= 10,
            "email": lambda x: "@" in str(x),
            "total_land_area": lambda x: float(x) > 0,
            "years_of_experience": lambda x: 0 <= int(x) <= 80
        }
        
        for field, rule in validation_rules.items():
            if field in collected_data:
                try:
                    if not rule(collected_data[field]):
                        validation_result["errors"].append(f"Invalid value for {field}")
                        validation_result["is_valid"] = False
                except:
                    validation_result["errors"].append(f"Invalid format for {field}")
                    validation_result["is_valid"] = False
        
        # Calculate completion boost
        if validation_result["is_valid"]:
            total_steps = len(self.workflow_definitions)
            validation_result["completion_boost"] = (1 / total_steps) * 100
        
        return validation_result
    
    async def _store_step_data(self, farmer_id: str, step_id: str, collected_data: Dict[str, Any]):
        """Store collected data for a workflow step"""
        try:
            # In a real implementation, this would store to database
            # For now, log the action
            logger.info(f"Storing data for farmer {farmer_id}, step {step_id}: {len(collected_data)} fields")
            
            # Store in MongoDB or other persistent storage
            # await self.data_coordinator.db_manager.update_farmer_profile(farmer_id, collected_data)
            
        except Exception as e:
            logger.error(f"Error storing step data: {e}")
            raise
    
    async def _trigger_post_step_actions(self, farmer_id: str, step: WorkflowStep, collected_data: Dict[str, Any]):
        """Trigger automated actions after completing a workflow step"""
        try:
            # Send welcome messages, notifications, or trigger other workflows
            actions_triggered = []
            
            # Example post-step actions
            if step.step_id == "basic_info":
                actions_triggered.append("send_welcome_message")
            elif step.step_id == "land_details":
                actions_triggered.append("generate_soil_health_recommendations")
            elif step.step_id == "current_crops":
                actions_triggered.append("setup_weather_alerts")
                actions_triggered.append("generate_crop_calendar")
            
            # Log actions (in real implementation, execute them)
            if actions_triggered:
                logger.info(f"Triggered post-step actions for {farmer_id}: {actions_triggered}")
            
        except Exception as e:
            logger.error(f"Error triggering post-step actions: {e}")
    
    def _analyze_personalization_factors(self, farmer_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze factors for personalizing the workflow"""
        factors = {
            "experience_level": farmer_data.get("years_of_experience", 0),
            "education_level": farmer_data.get("education_level", "unknown"),
            "farm_size": farmer_data.get("total_land_area", 0),
            "technology_adoption": context.get("tech_comfort", "medium"),
            "language_preference": farmer_data.get("preferred_language", "local"),
            "time_availability": context.get("time_availability", "medium")
        }
        
        return factors
    
    def _personalize_workflow_step(self, step: WorkflowStep, farmer_data: Dict[str, Any], 
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Personalize a workflow step based on farmer context"""
        personalized_step = step.__dict__.copy()
        
        # Adjust estimated time based on farmer's experience and education
        time_multiplier = 1.0
        if farmer_data.get("years_of_experience", 0) > 10:
            time_multiplier *= 0.8  # Experienced farmers are faster
        if farmer_data.get("education_level") in ["college", "university"]:
            time_multiplier *= 0.9  # Educated farmers adapt quicker
        
        personalized_step["estimated_time_minutes"] = int(step.estimated_time_minutes * time_multiplier)
        
        # Add personalized hints and examples
        personalized_step["personalization_notes"] = self._generate_personalization_notes(step, farmer_data)
        
        return personalized_step
    
    def _generate_personalization_notes(self, step: WorkflowStep, farmer_data: Dict[str, Any]) -> List[str]:
        """Generate personalized notes for a workflow step"""
        notes = []
        
        if step.step_id == "land_details":
            farm_size = farmer_data.get("total_land_area", 0)
            if farm_size > 5:
                notes.append("As a larger farm owner, consider GPS mapping for precise area calculation")
            else:
                notes.append("For small farms, pacing method can be used for area estimation")
        
        elif step.step_id == "current_crops":
            experience = farmer_data.get("years_of_experience", 0)
            if experience > 15:
                notes.append("Share your crop rotation strategies and intercropping experiences")
            else:
                notes.append("Focus on main crops and any challenges faced")
        
        return notes
    
    def _generate_contextual_recommendations(self, farmer_data: Dict[str, Any], 
                                           context: Dict[str, Any], progress: ProfileProgress) -> List[str]:
        """Generate contextual recommendations for the farmer"""
        recommendations = []
        
        # Season-based recommendations
        current_month = datetime.now().month
        if current_month in [3, 4, 5]:  # Spring
            recommendations.append("Consider updating your soil health data before planting season")
        elif current_month in [10, 11, 12]:  # Post-harvest
            recommendations.append("Perfect time to complete crop history and yield data")
        
        # Progress-based recommendations
        if progress.completion_level == ProfileCompletionLevel.BASIC:
            recommendations.append("Complete basic profiling to unlock weather alerts and market prices")
        elif progress.completion_level == ProfileCompletionLevel.INTERMEDIATE:
            recommendations.append("Add farm details to get personalized crop recommendations")
        
        return recommendations
    
    def _calculate_engagement_metrics(self, farmer_id: str) -> Dict[str, Any]:
        """Calculate engagement metrics for farmer"""
        return {
            "profile_completion_rate": self.farmer_progress[farmer_id].completion_percentage,
            "last_activity_days_ago": (datetime.utcnow() - self.farmer_progress[farmer_id].last_updated).days,
            "completion_velocity": "steady",  # Would calculate based on historical data
            "engagement_score": 75  # Would calculate based on various factors
        }
    
    def _assess_data_quality(self, farmer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess quality of farmer's profile data"""
        return {
            "completeness_score": 85,  # Based on filled vs total fields
            "accuracy_indicators": ["phone_verified", "location_verified"],
            "freshness_score": 90,  # Based on recent updates
            "consistency_score": 95  # Based on data validation checks
        }
    
    def _generate_journey_timeline(self, farmer_id: str) -> List[Dict[str, Any]]:
        """Generate farmer's profiling journey timeline"""
        # This would be built from historical data
        return [
            {"date": "2024-01-15", "event": "Profile Created", "stage": "registration"},
            {"date": "2024-01-20", "event": "Basic Info Completed", "stage": "basic_profiling"},
            {"date": "2024-02-01", "event": "Farm Details Added", "stage": "farm_details"}
        ]
    
    def _assess_recommendations_impact(self, farmer_id: str) -> Dict[str, Any]:
        """Assess impact of recommendations provided"""
        return {
            "recommendations_given": 12,
            "recommendations_followed": 8,
            "estimated_yield_improvement": "15%",
            "cost_savings": "₹5000"
        }
    
    def _identify_next_milestones(self, progress: ProfileProgress) -> List[Dict[str, Any]]:
        """Identify next milestones for farmer"""
        milestones = []
        
        if progress.completion_percentage < 50:
            milestones.append({
                "milestone": "Complete Basic Profile",
                "target_percentage": 50,
                "estimated_steps": 3,
                "benefits": ["Weather alerts", "Basic recommendations"]
            })
        elif progress.completion_percentage < 80:
            milestones.append({
                "milestone": "Advanced Analytics Ready",
                "target_percentage": 80,
                "estimated_steps": 5,
                "benefits": ["Soil health analysis", "Crop recommendations", "Yield predictions"]
            })
        
        return milestones

# Example usage and testing
async def main():
    """Example usage of Progressive Workflow Manager"""
    
    # This would normally be injected
    data_coordinator = None  # DataCoordinator()
    
    # Create workflow manager
    workflow_manager = ProgressiveWorkflowManager(data_coordinator)
    
    # Example: Initialize farmer profile
    farmer_id = "FARM001"
    initial_data = {
        "farmer_name": "Rajesh Kumar",
        "phone_number": "9876543210",
        "village": "Rampur",
        "district": "Meerut",
        "state": "Uttar Pradesh",
        "data_consent": True,
        "privacy_policy_accepted": True
    }
    
    progress = await workflow_manager.initialize_farmer_profile(farmer_id, initial_data)
    print(f"Initial progress: {progress.completion_percentage:.1f}%")
    
    # Get next steps
    next_steps = await workflow_manager.get_next_workflow_steps(farmer_id)
    print(f"Next recommended steps: {[step.step_name for step in next_steps]}")
    
    # Execute a workflow step
    if next_steps:
        step_data = {
            "years_of_experience": 15,
            "primary_occupation": "farming",
            "farming_methods": ["organic", "traditional"]
        }
        
        result = await workflow_manager.execute_workflow_step(
            farmer_id, next_steps[0].step_id, step_data
        )
        print(f"Step execution: {result['success']}")
    
    # Generate personalized workflow
    personalized_plan = await workflow_manager.generate_personalized_workflow(farmer_id)
    print(f"Personalized workflow with {len(personalized_plan['recommended_workflow'])} steps")

if __name__ == "__main__":
    asyncio.run(main())