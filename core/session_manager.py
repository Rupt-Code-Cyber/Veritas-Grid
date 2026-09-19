import os
import redis
import structlog

logger = structlog.get_logger()

# 🌟 Structural Blueprint Hook: Establish a persistent shared tracking layer at module initialization level
GLOBAL_PERSISTENT_MOCK_CACHE = {}

class ChatSessionManager:
    def __init__(self, redis_host: str = "redis_broker", redis_port: int = 6379):
        """Initializes connection to volatile transactional cache matrices."""
        self.is_mock_mode = os.getenv("ENVIRONMENT") == "testing"
        # Binds instance references cleanly to the immutable global module memory layout footprint
        self.mock_db = GLOBAL_PERSISTENT_MOCK_CACHE
        
        if not self.is_mock_mode:
            try:
                self.client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True, socket_timeout=2.0)
            except Exception as e:
                logger.error("Redis connection initiation failure", error=str(e))
                self.is_mock_mode = True

    def get_or_create_session(self, tracker_token: str) -> dict:
        """Retrieves active interactive menu tracking matrices or builds a clean state baseline."""
        if self.is_mock_mode:
            if tracker_token not in self.mock_db:
                self.mock_db[tracker_token] = {"current_state": "AWAITING_ORG_SELECTION", "target_tenant_id": "UNKNOWN"}
            return self.mock_db[tracker_token]
            
        try:
            state = self.client.hgetall(f"session:{tracker_token}")
            if not state:
                initial_state = {"current_state": "AWAITING_ORG_SELECTION", "target_tenant_id": "UNKNOWN"}
                self.client.hset(f"session:{tracker_token}", mapping=initial_state)
                self.client.expire(f"session:{tracker_token}", 3600)
                return initial_state
            return state
        except redis.RedisError as e:
            logger.error("Redis read connection failed. Falling back to non-blocking runtime state.", error=str(e))
            return {"current_state": "AWAITING_ORG_SELECTION", "target_tenant_id": "UNKNOWN"}

    def update_session(self, tracker_token: str, updates: dict) -> bool:
        """Applies mutation parameters to active conversation blocks."""
        if self.is_mock_mode:
            if tracker_token not in self.mock_db:
                self.mock_db[tracker_token] = {"current_state": "AWAITING_ORG_SELECTION", "target_tenant_id": "UNKNOWN"}
            self.mock_db[tracker_token].update(updates)
            return True
            
        try:
            self.client.hset(f"session:{tracker_token}", mapping=updates)
            return True
        except redis.RedisError as e:
            logger.error("Failed executing transactional memory updates", error=str(e))
            return False

    def terminate_session(self, tracker_token: str) -> bool:
        """Wipes tracking data fields entirely once a transaction loop concludes successfully."""
        if self.is_mock_mode:
            self.mock_db.pop(tracker_token, None)
            return True
            
        try:
            self.client.delete(f"session:{tracker_token}")
            return True
        except redis.RedisError as e:
            logger.error("Failed executing cache session cleanup sequences", error=str(e))
            return False
