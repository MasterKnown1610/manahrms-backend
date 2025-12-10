from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.api.v1.models.chat_model import ChatRoomType, ChatRoomMemberRole


class ChatRoomCreate(BaseModel):
    """Schema for creating a chat room"""
    name: Optional[str] = Field(None, max_length=255, description="Room name (required for group chats)")
    type: ChatRoomType = Field(ChatRoomType.GROUP, description="Room type: individual or group")
    member_user_ids: List[int] = Field(default_factory=list, description="User IDs (from users table, NOT employee IDs) to add to the room. For individual chats, provide exactly one user ID.")


class ChatRoomMemberAdd(BaseModel):
    """Schema for adding a member to a group chat"""
    user_id: int = Field(..., description="User ID to add to the group")


class ChatMessageCreate(BaseModel):
    """Schema for creating a chat message"""
    message: str = Field(..., min_length=1, max_length=5000, description="Message content")


class UserInfo(BaseModel):
    """Schema for user information in chat responses"""
    id: int
    username: str
    full_name: str
    email: str
    
    model_config = {"from_attributes": True}


class UserDropdownResponse(BaseModel):
    """Schema for user dropdown selection (for chat member selection)"""
    id: int
    username: str
    full_name: str
    email: str
    role: str  # 'admin' or 'employee'
    
    model_config = {"from_attributes": True}


class ChatRoomMemberResponse(BaseModel):
    """Schema for chat room member response"""
    id: int
    user_id: int
    role: ChatRoomMemberRole
    joined_at: datetime
    user: UserInfo
    
    model_config = {"from_attributes": True}


class ChatMessageResponse(BaseModel):
    """Schema for chat message response"""
    id: int
    chat_room_id: int
    sender_user_id: int
    message: str
    is_read: bool
    created_at: datetime
    sender: UserInfo
    
    model_config = {"from_attributes": True}


class ChatRoomResponse(BaseModel):
    """Schema for chat room response"""
    id: int
    company_id: int
    name: Optional[str]
    type: ChatRoomType
    created_by_user_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    members: List[ChatRoomMemberResponse] = []
    last_message: Optional[ChatMessageResponse] = None
    unread_count: int = 0
    
    model_config = {"from_attributes": True}


class ChatRoomListResponse(BaseModel):
    """Schema for listing chat rooms with summary"""
    id: int
    name: Optional[str]
    type: ChatRoomType
    created_at: datetime
    updated_at: datetime
    last_message: Optional[ChatMessageResponse] = None
    unread_count: int = 0
    member_count: int = 0
    other_user: Optional[UserInfo] = None  # For individual chats, shows the other person
    
    model_config = {"from_attributes": True}

