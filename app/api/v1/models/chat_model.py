from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class ChatRoomType(str, enum.Enum):
    """Chat room type enumeration"""
    INDIVIDUAL = "individual"  # 1-on-1 chat
    GROUP = "group"  # Group chat


class ChatRoomMemberRole(str, enum.Enum):
    """Chat room member role"""
    ADMIN = "admin"  # Group admin (can add/remove members)
    MEMBER = "member"  # Regular member


class ChatRoom(Base):
    """
    Chat room model for individual and group chats.
    Individual chats are created automatically when two users start chatting.
    Group chats are created explicitly with a name.
    """
    __tablename__ = "chat_rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=True)  # Name for group chats, null for individual chats
    type = Column(Enum(ChatRoomType), default=ChatRoomType.INDIVIDUAL, nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    members = relationship("ChatRoomMember", back_populates="chat_room", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="chat_room", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatRoom {self.id} - {self.name or 'Individual'} ({self.type.value})>"


class ChatRoomMember(Base):
    """
    Chat room members model.
    Tracks which users are in which chat rooms.
    """
    __tablename__ = "chat_room_members"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(ChatRoomMemberRole), default=ChatRoomMemberRole.MEMBER, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)  # For soft removal from group
    
    # Relationships
    chat_room = relationship("ChatRoom", back_populates="members")
    user = relationship("User")
    
    def __repr__(self):
        return f"<ChatRoomMember {self.user_id} in Room {self.chat_room_id}>"


class ChatMessage(Base):
    """
    Chat message model.
    Stores all messages in chat rooms.
    """
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)  # For future read receipts
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chat_room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_user_id])
    
    def __repr__(self):
        return f"<ChatMessage {self.id} in Room {self.chat_room_id}>"

