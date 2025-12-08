from pymongo import MongoClient
from app.config import get_settings
from typing import List, Dict, Optional
from math import radians, cos, sin, atan2, sqrt
import structlog

logger = structlog.get_logger()
settings = get_settings()

class BranchService:
    """Handle multi-branch hospital operations - Saylani Welfare (Free Services)"""

    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db = None
        self.branches_collection = None

    async def connect(self):
        """Initialize Mongodb client"""

        try:
            self.client = MongoClient(settings.MONGODB_URI)
            self.db = self.client[settings.MONGODB_DB_NAME]
            self.branches_collection = self.db['hospital_branches']

            self.branches_collection.create_index(
                [
                    (
                        "location", "2dsphere"
                    )
                ]
            )

            logger.info("branch_service_connected")
        except Exception as e:
            logger.error("branch_service_connection_failed", error=str(e))
            raise
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("branch_service_disconnected")

    async def get_nearest_branch(
        self,
        user_location: Dict[str, float],
        limit: int = 3,
        max_distance_km: float = 50.0
    ) -> List[Dict]:
        """
        Find nearest branches to user location
        
        Args:
            user_location: {"lat": 24.8607, "lng": 67.0011}
            limit: Number of branches to return
            max_distance_km: Maximum search radius
        """
        try:
            query = {
                "location": {
                    "$near": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates" : [
                                user_location["lng"],
                                user_location["lat"]
                            ]
                        },
                        "$max_distance": max_distance_km * 1000
                    }
                },
                "is_active": True
            }

            branches = list(self.branches_collection.find(
                query,
                {"_id": 0}
            ).limit(limit))

            for branch in branches:
                coords = branch["location"]["coordinates"]
                branch_loc = {"lng": coords[0], "lat": coords[1]}

                distance = self.calculate_distance(user_location, branch_loc)
                branch["distance_km"] = round(distance, 2)
                branch["distance_display"] = self.format_distance(distance)
            
            logger.info(
                "nearest_branch_found",
                user_location=user_location,
                branches_found=len(branches)
            )

            return branches

        except Exception as e:
            logger.error("get_nearest_branches_failed", error=str(e))
            return []

    def calculate_distance(
        self,
        loc1: Dict[str, float],
        loc2: Dict[str, float]
    ) -> float:
        """
        Calculate distance between two points using Haversine formula
        Returns distance in kilometers
        """
        R = 6371

        lat1, lon1 = radians(loc1["lat"]), radians(loc1["lng"])
        lat2, lon2 = radians(loc2["lat"]), radians(loc2["lng"])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c

    def format_distance(self, distance_km: float) -> str:
        """Format distance for display"""
        if distance_km < 1:
            return f"{int(distance_km * 1000)} meters"
        else:
            return f"{distance_km:.1f} km"
    async def get_branch_by_id(self, branch_id: str) -> Optional[Dict]:
        """Get branch details by ID"""

        try:
            branch = self.branches_collection.findone(
                {branch_id: branch_id, "is_active": True},
                {"_id": 0}
            )
            return branch
        except Exception as e:
            logger.error("get_branch_failed", branch_id=branch_id, error=str(e))
            return None
    
    async def check_speciality_availablity(
        self,
        speciality: str,
        user_location: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """Check which branches have a specific specialty"""
        try:
            query = {
                "specialities_available": {"$regex": speciality, "$options": "i"},
                "is_active": True
            }
            branches = list(self.branches_collection.find(query, {"_id":0}))

            if user_location:
                for branch in branches:
                    coords = branch['location']['coordinates']
                    branch_loc = {"lng": coords[0], "lat": coords[1]}
                    distance = self.calculate_distance(user_location, branch_loc)
                    branch['distance_km'] = round(distance, 2)

                branches.sort(key=lambda x: x.get('distance_km', float('inf')))
            return branches

        except Exception as e:
            logger.error("check_speciality_failed", speciality=speciality, error=str(e))
            return []

    async def check_service_availability(self, service_name: str, user_location: Optional[Dict[str, float]] = None) -> List[Dict]:
        """Check which branches offer a specific treatment service (ALL FREE)"""
        try:
            services_collection = self.db["treatment_services"]
            service = services_collection.find_one(
                {
                    "$or": [
                        {"service_name": {"$regex": service_name, "$options": "i"}},
                        {"service_name_urdu": {"$regex": service_name, "$options": "i"}}
                    ]
                },
                {"_id": 0}
            )

            if not service:
                return []

            available_branches = service.get("available_at_branches", [])
            branch_ids = [b["branch_id"] for b in available_branches]

            branches = list(self.branches_collection.find(
                {"branch_id": {"$in": branch_ids}, "is_active": True},
                {"_id": 0}
            ))

            for branch in branches:
                service_info = next(
                    (b for b in available_branches if b["branch_id"] == branch["branch_id"]),
                    None
                )
                if service_info:
                    branch["service_waiting_time"] = service_info.get("waiting_time")
                    branch["is_free"] = service_info.get("is_free", True)

            if user_location:
                for branch in branches:
                    coords = branch["location"]["coordinates"]
                    branch_loc = {"lng": coords[0], "lat": coords[1]}
                    distance = self.calculate_distance(user_location, branch_loc)
                    branch["distance_km"] = round(distance, 2)

                branches.sort(key=lambda x: x.get("distance_km", float('inf')))
            return branches

        except Exception as e:
            logger.error("check_service_failed", service=service_name, error=str(e))
            return []

    def format_branch_info(
        self,
        branch: Dict,
        language: str = "urdu",
        include_distance: bool = True
    ) -> str:
        """Format branch information for display - FREE SERVICE"""
        if language == "urdu":
            text = f"**{branch['branch_name']}**\n"
            text += f"   علاقہ: {branch['area']}, {branch['city']}\n"
            
            if include_distance and "distance_km" in branch:
                text += f"   فاصلہ: {branch['distance_display']}\n"
            
            text += f"   پتہ: {branch['full_address']}\n"
            text += f"   فون: {branch['contact']['phone']}\n"
            
            if branch.get('timings'):
                text += f"   اوقات: {branch['timings']['weekdays']}\n"
            
            if branch.get('services', {}).get('emergency'):
                text += f"   24/7 ایمرجنسی:\n"
            
            text += f"   **مفت علاج**\n"
            
        else:  # English
            text = f"**{branch['branch_name']}**\n"
            text += f"   Area: {branch['area']}, {branch['city']}\n"
            
            if include_distance and "distance_km" in branch:
                text += f"   Distance: {branch['distance_display']}\n"
            
            text += f"   Address: {branch['full_address']}\n"
            text += f"   Phone: {branch['contact']['phone']}\n"
            
            if branch.get('timings'):
                text += f"   Timings: {branch['timings']['weekdays']}\n"
            
            if branch.get('services', {}).get('emergency'):
                text += f"  24/7 Emergency:\n"
            
            text += f"   **Free Treatment**\n"
        
        return text


branch_service = BranchService()