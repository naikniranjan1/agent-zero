"""
User Management System for Agent Zero
Handles user authentication, sessions, and data isolation
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from python.helpers.mongodb_client import get_mongodb_client
from python.helpers.print_style import PrintStyle


@dataclass
class User:
    """User data model"""
    user_id: str
    username: str
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
    settings: Optional[Dict[str, Any]] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.last_active:
            data['last_active'] = self.last_active.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User from dictionary"""
        # Convert ISO strings back to datetime objects
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'last_active' in data and isinstance(data['last_active'], str):
            data['last_active'] = datetime.fromisoformat(data['last_active'])
        
        return cls(**data)


@dataclass
class UserSession:
    """User session data model"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    last_accessed: datetime
    is_active: bool = True
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        """Create UserSession from dictionary"""
        return cls(
            session_id=data['session_id'],
            user_id=data['user_id'],
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            last_accessed=datetime.fromisoformat(data['last_accessed']),
            is_active=data.get('is_active', True)
        )


class UserManager:
    """User management system"""
    
    def __init__(self):
        self.users_collection = "users"
        self.sessions_collection = "user_sessions"
        self.session_duration = timedelta(days=30)  # 30 days session
    
    async def _get_collection(self, collection_name: str):
        """Get MongoDB collection"""
        mongodb_client = await get_mongodb_client()
        if not await mongodb_client.ensure_connected():
            return None
        return mongodb_client.get_collection(collection_name)
    
    async def create_user(
        self, 
        username: str, 
        email: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[User]:
        """Create a new user"""
        try:
            collection = await self._get_collection(self.users_collection)
            if not collection:
                return None
            
            # Check if username already exists
            existing = await collection.find_one({"username": username})
            if existing:
                PrintStyle.warning(f"Username '{username}' already exists")
                return None
            
            # Create new user
            if not user_id:
                user_id = str(uuid.uuid4())
            
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                created_at=datetime.utcnow(),
                last_active=datetime.utcnow(),
                settings={}
            )
            
            # Insert into database
            await collection.insert_one(user.to_dict())
            
            PrintStyle.success(f"Created user: {username} (ID: {user_id})")
            return user
            
        except Exception as e:
            PrintStyle.error(f"Failed to create user: {str(e)}")
            return None
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            collection = await self._get_collection(self.users_collection)
            if not collection:
                return None
            
            user_data = await collection.find_one({"user_id": user_id})
            if not user_data:
                return None
            
            return User.from_dict(user_data)
            
        except Exception as e:
            PrintStyle.error(f"Failed to get user: {str(e)}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            collection = await self._get_collection(self.users_collection)
            if not collection:
                return None
            
            user_data = await collection.find_one({"username": username})
            if not user_data:
                return None
            
            return User.from_dict(user_data)
            
        except Exception as e:
            PrintStyle.error(f"Failed to get user by username: {str(e)}")
            return None
    
    async def update_user_activity(self, user_id: str) -> bool:
        """Update user's last activity timestamp"""
        try:
            collection = await self._get_collection(self.users_collection)
            if not collection:
                return False
            
            result = await collection.update_one(
                {"user_id": user_id},
                {"$set": {"last_active": datetime.utcnow().isoformat()}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            PrintStyle.error(f"Failed to update user activity: {str(e)}")
            return False
    
    async def create_session(self, user_id: str) -> Optional[UserSession]:
        """Create a new user session"""
        try:
            collection = await self._get_collection(self.sessions_collection)
            if not collection:
                return None
            
            # Create session
            session = UserSession(
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + self.session_duration,
                last_accessed=datetime.utcnow()
            )
            
            # Insert into database
            await collection.insert_one(session.to_dict())
            
            # Update user activity
            await self.update_user_activity(user_id)
            
            PrintStyle.success(f"Created session for user: {user_id}")
            return session
            
        except Exception as e:
            PrintStyle.error(f"Failed to create session: {str(e)}")
            return None
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        try:
            collection = await self._get_collection(self.sessions_collection)
            if not collection:
                return None
            
            session_data = await collection.find_one({"session_id": session_id})
            if not session_data:
                return None
            
            session = UserSession.from_dict(session_data)
            
            # Check if session is expired
            if session.is_expired:
                await self.invalidate_session(session_id)
                return None
            
            # Update last accessed
            await collection.update_one(
                {"session_id": session_id},
                {"$set": {"last_accessed": datetime.utcnow().isoformat()}}
            )
            
            return session
            
        except Exception as e:
            PrintStyle.error(f"Failed to get session: {str(e)}")
            return None
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session"""
        try:
            collection = await self._get_collection(self.sessions_collection)
            if not collection:
                return False
            
            result = await collection.update_one(
                {"session_id": session_id},
                {"$set": {"is_active": False}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            PrintStyle.error(f"Failed to invalidate session: {str(e)}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        try:
            collection = await self._get_collection(self.sessions_collection)
            if not collection:
                return 0
            
            # Delete expired sessions
            result = await collection.delete_many({
                "expires_at": {"$lt": datetime.utcnow().isoformat()}
            })
            
            if result.deleted_count > 0:
                PrintStyle.success(f"Cleaned up {result.deleted_count} expired sessions")
            
            return result.deleted_count
            
        except Exception as e:
            PrintStyle.error(f"Failed to cleanup sessions: {str(e)}")
            return 0
    
    async def get_or_create_default_user(self) -> Optional[User]:
        """Get or create a default user for single-user mode"""
        default_username = "default_user"
        
        # Try to get existing default user
        user = await self.get_user_by_username(default_username)
        if user:
            return user
        
        # Create default user
        return await self.create_user(
            username=default_username,
            email=None,
            user_id="default"
        )


# Global user manager instance
_user_manager: Optional[UserManager] = None


async def get_user_manager() -> UserManager:
    """Get or create the global user manager"""
    global _user_manager
    
    if _user_manager is None:
        _user_manager = UserManager()
    
    return _user_manager
