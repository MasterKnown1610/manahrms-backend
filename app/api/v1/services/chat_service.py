from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from datetime import datetime

from app.api.v1.models.chat_model import ChatRoom, ChatMessage, ChatRoomMember, ChatRoomType, ChatRoomMemberRole
from app.api.v1.models.user_model import User
from app.api.v1.schemas.chat_schema import ChatRoomCreate, ChatMessageCreate, ChatRoomMemberAdd


class ChatService:
    """Service for chat operations"""

    @staticmethod
    def create_individual_chat_room(
        db: Session,
        company_id: int,
        user1_id: int,
        user2_id: int
    ) -> ChatRoom:
        """
        Create or get an individual chat room between two users.
        Returns existing room if one already exists.
        """
        if user1_id == user2_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create chat room with yourself"
            )
        
        # Check if both users belong to the company
        user1 = db.query(User).filter(User.id == user1_id, User.company_id == company_id).first()
        user2 = db.query(User).filter(User.id == user2_id, User.company_id == company_id).first()
        
        if not user1 or not user2:
            missing_users = []
            if not user1:
                missing_users.append(f"User ID {user1_id}")
            if not user2:
                missing_users.append(f"User ID {user2_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"One or more users not found in company: {', '.join(missing_users)}. Note: member_user_ids expects User IDs (from users table), not Employee IDs."
            )
        
        # Check if individual chat room already exists between these two users
        # Find rooms that have both users as members
        existing_rooms = db.query(ChatRoom).join(
            ChatRoomMember, ChatRoom.id == ChatRoomMember.chat_room_id
        ).filter(
            ChatRoom.company_id == company_id,
            ChatRoom.type == ChatRoomType.INDIVIDUAL,
            ChatRoom.is_active == True,
            ChatRoomMember.user_id.in_([user1_id, user2_id]),
            ChatRoomMember.is_active == True
        ).group_by(ChatRoom.id).having(
            func.count(ChatRoomMember.user_id.distinct()) == 2
        ).all()
        
        existing_room = existing_rooms[0] if existing_rooms else None
        
        if existing_room:
            return existing_room
        
        # Create new individual chat room
        chat_room = ChatRoom(
            company_id=company_id,
            type=ChatRoomType.INDIVIDUAL,
            created_by_user_id=user1_id,
            is_active=True
        )
        db.add(chat_room)
        db.flush()
        
        # Add both users as members
        member1 = ChatRoomMember(
            chat_room_id=chat_room.id,
            user_id=user1_id,
            role=ChatRoomMemberRole.MEMBER,
            is_active=True
        )
        member2 = ChatRoomMember(
            chat_room_id=chat_room.id,
            user_id=user2_id,
            role=ChatRoomMemberRole.MEMBER,
            is_active=True
        )
        db.add(member1)
        db.add(member2)
        db.commit()
        db.refresh(chat_room)
        
        return chat_room

    @staticmethod
    def create_group_chat_room(
        db: Session,
        company_id: int,
        creator_user_id: int,
        data: ChatRoomCreate
    ) -> ChatRoom:
        """
        Create a group chat room.
        """
        if not data.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group name is required"
            )
        
        # Check if creator belongs to company
        creator = db.query(User).filter(
            User.id == creator_user_id,
            User.company_id == company_id
        ).first()
        
        if not creator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Creator user not found"
            )
        
        # Validate all member user IDs belong to company
        if data.member_user_ids:
            member_users = db.query(User).filter(
                User.id.in_(data.member_user_ids),
                User.company_id == company_id
            ).all()
            
            if len(member_users) != len(data.member_user_ids):
                found_ids = {u.id for u in member_users}
                missing_ids = [uid for uid in data.member_user_ids if uid not in found_ids]
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"One or more users not found in company: User IDs {missing_ids}. Note: member_user_ids expects User IDs (from users table), not Employee IDs."
                )
        
        # Create group chat room
        chat_room = ChatRoom(
            company_id=company_id,
            name=data.name,
            type=ChatRoomType.GROUP,
            created_by_user_id=creator_user_id,
            is_active=True
        )
        db.add(chat_room)
        db.flush()
        
        # Add creator as admin
        creator_member = ChatRoomMember(
            chat_room_id=chat_room.id,
            user_id=creator_user_id,
            role=ChatRoomMemberRole.ADMIN,
            is_active=True
        )
        db.add(creator_member)
        
        # Add other members
        for user_id in data.member_user_ids:
            if user_id != creator_user_id:  # Don't add creator twice
                member = ChatRoomMember(
                    chat_room_id=chat_room.id,
                    user_id=user_id,
                    role=ChatRoomMemberRole.MEMBER,
                    is_active=True
                )
                db.add(member)
        
        db.commit()
        db.refresh(chat_room)
        
        return chat_room

    @staticmethod
    def get_user_chat_rooms(
        db: Session,
        company_id: int,
        user_id: int
    ) -> List[ChatRoom]:
        """
        Get all chat rooms for a user.
        """
        return db.query(ChatRoom).join(
            ChatRoomMember, ChatRoom.id == ChatRoomMember.chat_room_id
        ).filter(
            ChatRoom.company_id == company_id,
            ChatRoomMember.user_id == user_id,
            ChatRoomMember.is_active == True,
            ChatRoom.is_active == True
        ).order_by(ChatRoom.updated_at.desc()).all()

    @staticmethod
    def get_chat_room_by_id(
        db: Session,
        company_id: int,
        room_id: int,
        user_id: int
    ) -> ChatRoom:
        """
        Get a chat room by ID, ensuring user is a member.
        """
        chat_room = db.query(ChatRoom).join(
            ChatRoomMember, ChatRoom.id == ChatRoomMember.chat_room_id
        ).filter(
            ChatRoom.id == room_id,
            ChatRoom.company_id == company_id,
            ChatRoomMember.user_id == user_id,
            ChatRoomMember.is_active == True,
            ChatRoom.is_active == True
        ).first()
        
        if not chat_room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat room not found or you don't have access"
            )
        
        return chat_room

    @staticmethod
    def send_message(
        db: Session,
        company_id: int,
        room_id: int,
        sender_user_id: int,
        data: ChatMessageCreate
    ) -> ChatMessage:
        """
        Send a message in a chat room.
        """
        # Verify user is a member of the room
        chat_room = ChatService.get_chat_room_by_id(db, company_id, room_id, sender_user_id)
        
        # Create message
        message = ChatMessage(
            chat_room_id=room_id,
            sender_user_id=sender_user_id,
            message=data.message,
            is_read=False
        )
        db.add(message)
        
        # Update room's updated_at timestamp
        chat_room.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(message)
        
        return message

    @staticmethod
    def get_chat_messages(
        db: Session,
        company_id: int,
        room_id: int,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[ChatMessage], int]:
        """
        Get messages in a chat room.
        """
        # Verify user is a member
        ChatService.get_chat_room_by_id(db, company_id, room_id, user_id)
        
        # Get messages
        query = db.query(ChatMessage).filter(
            ChatMessage.chat_room_id == room_id
        )
        
        total = query.count()
        
        messages = query.order_by(
            desc(ChatMessage.created_at)
        ).offset(offset).limit(limit).all()
        
        # Reverse to get chronological order (oldest first)
        messages.reverse()
        
        return messages, total

    @staticmethod
    def add_member_to_group(
        db: Session,
        company_id: int,
        room_id: int,
        admin_user_id: int,
        data: ChatRoomMemberAdd
    ) -> ChatRoomMember:
        """
        Add a member to a group chat (admin only).
        """
        # Get room and verify it's a group
        chat_room = ChatService.get_chat_room_by_id(db, company_id, room_id, admin_user_id)
        
        if chat_room.type != ChatRoomType.GROUP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only add members to group chats"
            )
        
        # Verify admin is actually an admin
        admin_member = db.query(ChatRoomMember).filter(
            ChatRoomMember.chat_room_id == room_id,
            ChatRoomMember.user_id == admin_user_id,
            ChatRoomMember.role == ChatRoomMemberRole.ADMIN
        ).first()
        
        if not admin_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group admins can add members"
            )
        
        # Check if user belongs to company
        user = db.query(User).filter(
            User.id == data.user_id,
            User.company_id == company_id
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in company"
            )
        
        # Check if user is already a member
        existing_member = db.query(ChatRoomMember).filter(
            ChatRoomMember.chat_room_id == room_id,
            ChatRoomMember.user_id == data.user_id,
            ChatRoomMember.is_active == True
        ).first()
        
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this group"
            )
        
        # Add member
        member = ChatRoomMember(
            chat_room_id=room_id,
            user_id=data.user_id,
            role=ChatRoomMemberRole.MEMBER,
            is_active=True
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        
        return member

    @staticmethod
    def remove_member_from_group(
        db: Session,
        company_id: int,
        room_id: int,
        admin_user_id: int,
        member_user_id: int
    ) -> None:
        """
        Remove a member from a group chat (admin only, or self-removal).
        """
        # Get room and verify it's a group
        chat_room = ChatService.get_chat_room_by_id(db, company_id, room_id, admin_user_id)
        
        if chat_room.type != ChatRoomType.GROUP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only remove members from group chats"
            )
        
        # Check if removing self (allowed) or if admin is removing someone else
        if admin_user_id != member_user_id:
            admin_member = db.query(ChatRoomMember).filter(
                ChatRoomMember.chat_room_id == room_id,
                ChatRoomMember.user_id == admin_user_id,
                ChatRoomMember.role == ChatRoomMemberRole.ADMIN
            ).first()
            
            if not admin_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only group admins can remove members"
                )
        
        # Find and deactivate member
        member = db.query(ChatRoomMember).filter(
            ChatRoomMember.chat_room_id == room_id,
            ChatRoomMember.user_id == member_user_id,
            ChatRoomMember.is_active == True
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in group"
            )
        
        member.is_active = False
        db.commit()

