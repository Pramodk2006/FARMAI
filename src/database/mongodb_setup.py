# STEP 1: Set up MongoDB Collections for Category 1 Data (Farmer/Static/Long-term)

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from datetime import datetime
import logging
from typing import Optional, Dict, Any, List
from bson import ObjectId
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDBSetup:
    """
    MongoDB setup and collection manager for agricultural AI system
    Handles farmer profiles, static data, and long-term agricultural data
    """
    
    def __init__(self, uri: str = None, db_name: str = "agricultural_ai"):
        """
        Initialize MongoDB connection
        
        Args:
            uri: MongoDB connection URI
            db_name: Database name
        """
        self.uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.db_name = db_name
        self.client = None  
        self.db = None  
        self.collections: dict = {}



    async def connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.uri)
            # Test connection
            await self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            logger.info(f"Successfully connected to MongoDB: {self.db_name}")
            
            # Initialize collections
            await self._setup_collections()
            await self._create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def _setup_collections(self):
        """Set up all required collections"""
        collection_names = [
            # Category 1: Farmer/Static/Long-term Data
            "farmer_profiles",
            "farm_details", 
            "crop_history",
            "land_records",
            "equipment_inventory",
            "certification_records",
            "financial_records",
            "insurance_policies",
            
            # Historical data for analysis
            "historical_yields",
            "seasonal_patterns",
            "long_term_trends",
            
            # Configuration and metadata
            "system_config",
            "data_schemas"
        ]
        
        for collection_name in collection_names:
            self.collections[collection_name] = self.db[collection_name]
            logger.info(f"Collection '{collection_name}' initialized")
    
    async def _create_indexes(self):
        """Create indexes for better query performance"""
        try:
            # Farmer profiles indexes
            await self.collections["farmer_profiles"].create_index([("farmer_id", 1)], unique=True)
            await self.collections["farmer_profiles"].create_index([("phone_number", 1)])
            await self.collections["farmer_profiles"].create_index([("location.district", 1)])
            await self.collections["farmer_profiles"].create_index([("registration_date", 1)])
            
            # Farm details indexes
            await self.collections["farm_details"].create_index([("farmer_id", 1)])
            await self.collections["farm_details"].create_index([("location.coordinates", "2dsphere")])
            await self.collections["farm_details"].create_index([("farm_size", 1)])
            await self.collections["farm_details"].create_index([("soil_type", 1)])
            
            # Crop history indexes
            await self.collections["crop_history"].create_index([("farmer_id", 1)])
            await self.collections["crop_history"].create_index([("crop_season", 1)])
            await self.collections["crop_history"].create_index([("crop_type", 1)])
            await self.collections["crop_history"].create_index([("harvest_date", 1)])
            
            # Land records indexes
            await self.collections["land_records"].create_index([("farmer_id", 1)])
            await self.collections["land_records"].create_index([("survey_number", 1)])
            await self.collections["land_records"].create_index([("ownership_type", 1)])
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            raise
    
    async def insert_farmer_profile(self, profile_data: Dict[str, Any]) -> str:
        """
        Insert farmer profile data
        
        Args:
            profile_data: Farmer profile information
            
        Returns:
            Inserted document ID
        """
        try:
            # Add timestamps and validation
            profile_data.update({
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "status": "active",
                "data_version": "1.0"
            })
            
            # Validate required fields
            required_fields = ["farmer_name", "phone_number", "location", "farmer_id"]
            for field in required_fields:
                if field not in profile_data:
                    raise ValueError(f"Required field '{field}' is missing")
            
            result = await self.collections["farmer_profiles"].insert_one(profile_data)
            logger.info(f"Farmer profile inserted: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error inserting farmer profile: {e}")
            raise
    
    async def insert_farm_details(self, farm_data: Dict[str, Any]) -> str:
        """
        Insert farm details
        
        Args:
            farm_data: Farm information
            
        Returns:
            Inserted document ID
        """
        try:
            farm_data.update({
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "verification_status": "pending"
            })
            
            result = await self.collections["farm_details"].insert_one(farm_data)
            logger.info(f"Farm details inserted: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error inserting farm details: {e}")
            raise
    
    async def insert_crop_history(self, crop_data: Dict[str, Any]) -> str:
        """
        Insert crop history record
        
        Args:
            crop_data: Crop history information
            
        Returns:
            Inserted document ID
        """
        try:
            crop_data.update({
                "recorded_at": datetime.utcnow(),
                "data_source": "manual_entry"
            })
            
            result = await self.collections["crop_history"].insert_one(crop_data)
            logger.info(f"Crop history inserted: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error inserting crop history: {e}")
            raise
    
    async def get_farmer_profile(self, farmer_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve farmer profile by ID
        
        Args:
            farmer_id: Farmer identifier
            
        Returns:
            Farmer profile data or None
        """
        try:
            profile = await self.collections["farmer_profiles"].find_one({"farmer_id": farmer_id})
            if profile:
                profile["_id"] = str(profile["_id"])
            return profile
            
        except Exception as e:
            logger.error(f"Error retrieving farmer profile: {e}")
            raise
    
    async def update_farmer_profile(self, farmer_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update farmer profile
        
        Args:
            farmer_id: Farmer identifier
            update_data: Data to update
            
        Returns:
            Success status
        """
        try:
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.collections["farmer_profiles"].update_one(
                {"farmer_id": farmer_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Farmer profile updated: {farmer_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating farmer profile: {e}")
            raise
    
    async def get_farms_by_location(self, district: str, state: str = None) -> List[Dict[str, Any]]:
        """
        Get farms by geographical location
        
        Args:
            district: District name
            state: State name (optional)
            
        Returns:
            List of farm records
        """
        try:
            query = {"location.district": district}
            if state:
                query["location.state"] = state
            
            cursor = self.collections["farm_details"].find(query)
            farms = []
            
            async for farm in cursor:
                farm["_id"] = str(farm["_id"])
                farms.append(farm)
            
            logger.info(f"Found {len(farms)} farms in {district}")
            return farms
            
        except Exception as e:
            logger.error(f"Error retrieving farms by location: {e}")
            raise
    
    async def get_crop_statistics(self, crop_type: str, season: str = None) -> Dict[str, Any]:
        """
        Get crop statistics and trends
        
        Args:
            crop_type: Type of crop
            season: Crop season (optional)
            
        Returns:
            Crop statistics
        """
        try:
            pipeline = [
                {"$match": {"crop_type": crop_type}},
                {
                    "$group": {
                        "_id": "$crop_type",
                        "total_farmers": {"$addToSet": "$farmer_id"},
                        "avg_yield": {"$avg": "$yield_per_acre"},
                        "total_area": {"$sum": "$area_planted"},
                        "harvest_dates": {"$push": "$harvest_date"}
                    }
                },
                {
                    "$project": {
                        "crop_type": "$_id",
                        "total_farmers": {"$size": "$total_farmers"},
                        "avg_yield": "$avg_yield",
                        "total_area": "$total_area",
                        "harvest_dates": "$harvest_dates"
                    }
                }
            ]
            
            if season:
                pipeline[0]["$match"]["crop_season"] = season
            
            cursor = self.collections["crop_history"].aggregate(pipeline)
            stats = await cursor.to_list(length=None)
            
            if stats:
                return stats[0]
            else:
                return {"crop_type": crop_type, "message": "No data found"}
                
        except Exception as e:
            logger.error(f"Error getting crop statistics: {e}")
            raise
    
    async def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

# Utility functions for data validation and processing

def validate_farmer_data(data: Dict[str, Any]) -> List[str]:
    """
    Validate farmer profile data
    
    Args:
        data: Farmer data to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    required_fields = {
        "farmer_name": str,
        "farmer_id": str,
        "phone_number": str,
        "location": dict
    }
    
    for field, field_type in required_fields.items():
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif not isinstance(data[field], field_type):
            errors.append(f"Invalid type for field {field}: expected {field_type.__name__}")
    
    # Validate phone number format
    if "phone_number" in data:
        phone = data["phone_number"]
        if not phone.isdigit() or len(phone) < 10:
            errors.append("Invalid phone number format")
    
    # Validate location structure
    if "location" in data and isinstance(data["location"], dict):
        required_location_fields = ["district", "state", "country"]
        for field in required_location_fields:
            if field not in data["location"]:
                errors.append(f"Missing location field: {field}")
    
    return errors

def create_farmer_profile_template() -> Dict[str, Any]:
    """
    Create a template for farmer profile data
    
    Returns:
        Template dictionary
    """
    return {
        "farmer_id": "",
        "farmer_name": "",
        "phone_number": "",
        "email": "",
        "date_of_birth": None,
        "gender": "",
        "education_level": "",
        "experience_years": 0,
        "location": {
            "address": "",
            "village": "",
            "district": "",
            "state": "",
            "country": "",
            "pincode": "",
            "coordinates": {
                "latitude": 0.0,
                "longitude": 0.0
            }
        },
        "family_details": {
            "family_size": 0,
            "dependents": 0,
            "occupation_others": []
        },
        "bank_details": {
            "account_number": "",
            "ifsc_code": "",
            "bank_name": "",
            "branch_name": ""
        },
        "documents": {
            "aadhar_number": "",
            "pan_number": "",
            "voter_id": "",
            "driving_license": "",
            "passport": ""
        },
        "preferences": {
            "communication_language": "english",
            "notification_preferences": {
                "sms": True,
                "email": False,
                "voice_call": False
            }
        },
        "verification_status": "pending",
        "data_consent": False,
        "created_at": None,
        "updated_at": None
    }

# Example usage and testing functions

async def example_usage():
    """Example usage of MongoDBSetup class"""
    
    # Initialize database
    db_setup = MongoDBSetup()
    await db_setup.connect()
    
    # Create sample farmer profile
    farmer_data = {
        "farmer_id": "FARM001",
        "farmer_name": "Rajesh Kumar",
        "phone_number": "9876543210",
        "email": "rajesh.kumar@example.com",
        "location": {
            "village": "Rampur",
            "district": "Meerut",
            "state": "Uttar Pradesh",
            "country": "India",
            "pincode": "250001",
            "coordinates": {
                "latitude": 28.9845,
                "longitude": 77.7064
            }
        },
        "experience_years": 15,
        "education_level": "High School",
        "data_consent": True
    }
    
    # Insert farmer profile
    profile_id = await db_setup.insert_farmer_profile(farmer_data)
    print(f"Inserted farmer profile with ID: {profile_id}")
    
    # Retrieve farmer profile
    profile = await db_setup.get_farmer_profile("FARM001")
    print(f"Retrieved profile: {profile['farmer_name']}")
    
    # Close connection
    await db_setup.close_connection()

if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())