from pymongo import MongoClient
from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.models.schemas import RAGQuery, RAGResult
from app.services.branch_service import branch_service
import structlog

logger = structlog.get_logger()
settings = get_settings()

class RAGService:
    """Handles Retrieval Augmented Generation using MongoDB Atlas Vector Search"""

    def __init__(self):
        self.client: Optional["MongoClient"] = None
        self.db = None
        self.doctors_collection = None
        self.vector_collection = None
        self.symptom_mapping_collection = None

    async def connect(self):
        """Initialize MongoDB connection"""
        try:
            self.client = MongoClient(settings.MONGODB_URI)
            self.db = self.client[settings.MONGODB_DB_NAME]
            self.doctors_collection = self.db[settings.MONGODB_COLLECTION]
            self.vector_collection = self.db[settings.MONGODB_VECTOR_COLLECTION]
            self.symptom_mapping_collection = self.db["symptom_mapping"]

            self.client.admin.command('ping')
            logger.info("mongodb_connected", database=settings.MONGODB_DB_NAME)
        except Exception as e:
            logger.error("mongodb_connection_failed", error=str(e))
            raise

    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("mongodb_disconnected")

    async def find_doctors_at_nearest_branches(
        self,
        speciality: str,
        user_location: Dict[str, float],
        max_branches: int = 3
    ) -> List[Dict]:
        """
        Find doctors of specific specialty at nearest branches
        """
        try:
            nearest_branches = branch_service.get_nearest_branch(
                user_location,
                limit=max_branches
            )

            if not nearest_branches:
                logger.warning("no_nearest_branch_found")
                return []

            branch_ids = [b['branch_id'] for b in nearest_branches]
            doctors = list(self.doctors_collection.find(
                {
                    "speciality": {"$regex": speciality, "$options": "i"},
                    "branches.branch_id": {"$in": branch_ids},
                    "is_active": True
                },
                {"_id": 0}
            ))

            for doctor in doctors:
                doctor['nearby_branches'] = [
                    b for b in doctor.get("branches", [])
                    if b["branch_id"] in branch_ids
                ]

                for doc_branch in doctor["nearby_branches"]:
                    branch_info = next(
                        (b for b in nearest_branches if b["branch_id"]==doc_branch["branch_id"]),
                        None
                    )

                    if branch_info:
                        doc_branch["branch_distance"] = branch_info["distance_km"]
                        doc_branch["branch_full_info"] = branch_info

            for doctor in doctors:
                if doctor.get("nearby_branches"):
                    min_distance = min(
                        b.get("branch_distance", float('inf'))
                        for b in doctor["nearest_branches"]
                    )
                    doctor["min_distance"] = min_distance
                else:
                    doctor["min_distance"] = float('inf')

            doctors.sort(key=lambda x: x.get("min_distance", float('inf')))

            logger.info(
                "doctors_found_at_branches",
                speciality=speciality,
                doctors_count=len(doctors)
            )

            return doctors
        
        except Exception as e:
            logger.error("find_doctors_at_branches_failed", error=str(e))
            return []

    async def map_symptoms_to_speciality(self, symptoms: List[str]) -> Optional[Dict]:
        """
        Map symptoms to medical specialty using symptom mapping database
        """
        try:
            if not symptoms:
                return None

            symptom_doc = self.symptom_mapping_collection.find_one({
                "symptoms": {"$in": symptoms}
            })

            if symptom_doc:
                logger.info(
                    "symptoms_mapped",
                    symptoms=symptoms,
                    speciality=symptom_doc.get("speciality")
                )
                return symptom_doc

            logger.warning("no_speciality_match", symptoms=symptoms)    
            return None

        except Exception as e:
            logger.error("symptom_mapping_failed", error=str(e))
            return None

    async def simple_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Simple keyword search for structured data (doctors, timings)
        """
        try:
            search_query = {
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"speciality": {"$regex": query, "$options": "i"}},
                    {"timings.day": {"$regex": query, "$options": "i"}},
                    {"branches.branch_name": {"$regex": query, "$options": "i"}}
                ]
            }

            results = list(self.doctors_collection.find(
                search_query,
                {'_id': 0}
            ).limit(5))

            logger.info("simple_search_complete", query=query, results_count=len(results))
            return results

        except Exception as e:
            logger.error("simple_search_failed", query=query, error=str(e))
            return []

    async def vector_search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Vector search for complex queries (treatment protocols, medical procedures)
        """
        try:
            pipeline = [
                {
                    "$vectorSearch": {
                            "index": "treatment_vector_index",
                            "path": "embedding",
                            "query_vector": self._get_embedding(query),
                            "numCandidates": 20,
                            "limit": limit
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "title": 1,
                        "content": 1,
                        "category": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]

            results = list(self.vector_collection.aggregate(pipeline))

            logger.info("vector_search_complete", query=query, results_count=len(results))
            return results

        except Exception as e:
            logger.error("vector_search_failed", query=query, error=str(e))
            return []

    async def _get_embeddings(self, text: str) -> List[float]:
        """Generate embedding for query using Gemini Embedding API"""
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)

        try:
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_query"
            )

            return result['embedding']

        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            return []

    async def smart_symptom_search(
        self,
        user_query: str,
        user_location: Optional[Dict[str, float]] = None,
        extracted_symptoms: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Smart search combining symptom mapping and location-based doctor search
        """
        try:
            if not extracted_symptoms:
                speciality = "General Medicine"
            else:
                symptom_mapping = self.map_symptoms_to_speciality(extracted_symptoms)
                speciality = symptom_mapping.get("speciality", "General Medicine") if symptom_mapping else "General Medicine"

            if user_location:
                doctors = await self.find_doctors_at_nearest_branches(
                    speciality=speciality,
                    user_location=user_location,
                    max_branches=3
                )
            else:
                doctors = list(self.doctors_collection.find(
                    {"speciality": {"$regex": speciality, "$options": "i"}, "is_active": True},
                    {"_id": 0}
                ).limit(5))

            return doctors

        except Exception as e:
            logger.error("smart_system_search_failed", error=str(e))
            return []

    async def search(self, rag_query: RAGQuery) -> RAGResult:
        """Main search method that routes to appropriate search type"""
        try:
            query = rag_query.query
            search_type = rag_query.search_type

            if search_type == "simple":
                results = await self.simple_search(query)
            elif search_type == "vector":
                results = await self.vector_search(query)
            elif search_type == "smart_symptom":
                results = await self.smart_symptom_search(
                    user_query=query,
                    user_location=rag_query.user_location
                )
            else:
                results = self.simple_search(query)

            return RAGResult(
                results=results,
                search_type=search_type,
                relevant_score=results[0].get('score') if results else None
            )

        except Exception as e:
            logger.error("rag_search_failed", query=rag_query.query, error=str(e))
            return RAGResult(results=[], search_type=search_type)

rag_service = RAGService()

