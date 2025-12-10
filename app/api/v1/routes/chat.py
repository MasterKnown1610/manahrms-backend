from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user
from app.api.v1.models.user_model import User, UserRole
from sqlalchemy import or_
from app.api.v1.models.chat_model import ChatRoom, ChatMessage, ChatRoomMember
from app.api.v1.schemas.chat_schema import (
    ChatRoomCreate,
    ChatRoomResponse,
    ChatRoomListResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatRoomMemberAdd,
    ChatRoomMemberResponse,
    UserInfo,
    UserDropdownResponse
)
from app.api.v1.schemas.user_schema import MessageResponse
from app.api.v1.services.chat_service import ChatService


router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/users/dropdown", response_model=List[UserDropdownResponse])
async def get_users_for_chat_dropdown(
    search: Optional[str] = Query(None, description="Search by username, full name, or email"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results to return"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get a list of users (User IDs) for chat member selection.
    
    IMPORTANT: Returns User IDs (from users table), NOT Employee IDs!
    Use these User IDs in member_user_ids when creating chat rooms.
    
    - Returns only active users from the same company
    - Supports search by username, full_name, or email
    - Limited to prevent returning huge datasets (default: 50, max: 100)
    - Excludes the current user (you can't chat with yourself)
    """
    query = db.query(User).filter(
        User.company_id == current_user.company_id,
        User.is_active == True,
        User.id != current_user.id  # Exclude current user
    )
    
    # Apply search filter if provided
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(search_pattern),
                User.full_name.ilike(search_pattern),
                User.email.ilike(search_pattern)
            )
        )
    
    users = query.order_by(User.full_name).limit(limit).all()
    
    return [UserDropdownResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        role=user.role.value
    ) for user in users]


@router.post("/rooms/create", response_model=ChatRoomResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_room(
    data: ChatRoomCreate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Create a chat room (individual or group).
    
    IMPORTANT: member_user_ids expects User IDs (from users table), NOT Employee IDs!
    Use GET /chat/users/dropdown to find available User IDs for chat.
    
    For individual chats:
    - Set type to 'individual'
    - Provide member_user_ids with exactly one User ID (the other person)
    
    For group chats:
    - Set type to 'group'
    - Provide a name for the group
    - Optionally provide member_user_ids to add members initially
    """
    if data.type == "individual":
        if not data.member_user_ids or len(data.member_user_ids) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Individual chat requires exactly one member user ID"
            )
        chat_room = ChatService.create_individual_chat_room(
            db=db,
            company_id=current_user.company_id,
            user1_id=current_user.id,
            user2_id=data.member_user_ids[0]
        )
    else:
        chat_room = ChatService.create_group_chat_room(
            db=db,
            company_id=current_user.company_id,
            creator_user_id=current_user.id,
            data=data
        )
    
    # Load relationships
    room_with_relations = (
        db.query(ChatRoom)
        .options(
            joinedload(ChatRoom.members).joinedload(ChatRoomMember.user),
            joinedload(ChatRoom.messages).joinedload(ChatMessage.sender)
        )
        .filter(ChatRoom.id == chat_room.id)
        .first()
    )
    
    return ChatRoomResponse.model_validate(room_with_relations)


@router.get("/rooms", response_model=List[ChatRoomListResponse])
async def get_my_chat_rooms(
    room_type: Optional[str] = Query(None, description="Filter by room type: 'individual' or 'group'"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get all chat rooms for the current user (like WhatsApp chat list).
    Returns rooms with last message, unread count, and other user info for individual chats.
    
    - For individual chats: Shows the other person's information
    - For group chats: Shows the group name
    - Filter by room_type to get only individual or group chats
    """
    from app.api.v1.models.chat_model import ChatRoomType
    
    rooms = ChatService.get_user_chat_rooms(
        db=db,
        company_id=current_user.company_id,
        user_id=current_user.id
    )
    
    # Filter by type if specified
    if room_type:
        if room_type == "individual":
            rooms = [r for r in rooms if r.type == ChatRoomType.INDIVIDUAL]
        elif room_type == "group":
            rooms = [r for r in rooms if r.type == ChatRoomType.GROUP]
    
    # Load last message and calculate unread count for each room
    result = []
    for room in rooms:
        # Get last message
        last_message = (
            db.query(ChatMessage)
            .options(joinedload(ChatMessage.sender))
            .filter(ChatMessage.chat_room_id == room.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        
        # Count unread messages (messages not sent by current user and not read)
        unread_count = db.query(ChatMessage).filter(
            ChatMessage.chat_room_id == room.id,
            ChatMessage.sender_user_id != current_user.id,
            ChatMessage.is_read == False
        ).count()
        
        # Count members
        member_count = db.query(ChatRoomMember).filter(
            ChatRoomMember.chat_room_id == room.id,
            ChatRoomMember.is_active == True
        ).count()
        
        # For individual chats, get the other user's information
        other_user = None
        if room.type == ChatRoomType.INDIVIDUAL:
            other_member = (
                db.query(ChatRoomMember)
                .options(joinedload(ChatRoomMember.user))
                .filter(
                    ChatRoomMember.chat_room_id == room.id,
                    ChatRoomMember.user_id != current_user.id,
                    ChatRoomMember.is_active == True
                )
                .first()
            )
            if other_member and other_member.user:
                other_user = UserInfo.model_validate(other_member.user)
        
        room_dict = {
            "id": room.id,
            "name": room.name,
            "type": room.type,
            "created_at": room.created_at,
            "updated_at": room.updated_at,
            "last_message": ChatMessageResponse.model_validate(last_message) if last_message else None,
            "unread_count": unread_count,
            "member_count": member_count,
            "other_user": other_user
        }
        result.append(ChatRoomListResponse(**room_dict))
    
    return result


@router.get("/rooms/{room_id}", response_model=ChatRoomResponse)
async def get_chat_room(
    room_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get a specific chat room with all members and last message.
    """
    room = ChatService.get_chat_room_by_id(
        db=db,
        company_id=current_user.company_id,
        room_id=room_id,
        user_id=current_user.id
    )
    
    # Load with relationships
    room_with_relations = (
        db.query(ChatRoom)
        .options(
            joinedload(ChatRoom.members).joinedload(ChatRoomMember.user),
            joinedload(ChatRoom.messages).joinedload(ChatMessage.sender)
        )
        .filter(ChatRoom.id == room_id)
        .first()
    )
    
    # Get last message
    last_message = (
        db.query(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .filter(ChatMessage.chat_room_id == room_id)
        .order_by(ChatMessage.created_at.desc())
        .first()
    )
    
    # Count unread messages
    unread_count = db.query(ChatMessage).filter(
        ChatMessage.chat_room_id == room_id,
        ChatMessage.sender_user_id != current_user.id,
        ChatMessage.is_read == False
    ).count()
    
    room_dict = ChatRoomResponse.model_validate(room_with_relations).model_dump()
    room_dict["last_message"] = ChatMessageResponse.model_validate(last_message) if last_message else None
    room_dict["unread_count"] = unread_count
    
    return ChatRoomResponse(**room_dict)


@router.get("/rooms/{room_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    room_id: int,
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get messages in a chat room with pagination.
    Returns messages in chronological order (oldest first).
    """
    messages, total = ChatService.get_chat_messages(
        db=db,
        company_id=current_user.company_id,
        room_id=room_id,
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )
    
    # Load sender information
    messages_with_sender = (
        db.query(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .filter(ChatMessage.id.in_([msg.id for msg in messages]))
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    
    return [ChatMessageResponse.model_validate(msg) for msg in messages_with_sender]


@router.post("/rooms/{room_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    room_id: int,
    data: ChatMessageCreate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Send a message in a chat room.
    """
    message = ChatService.send_message(
        db=db,
        company_id=current_user.company_id,
        room_id=room_id,
        sender_user_id=current_user.id,
        data=data
    )
    
    # Load sender information
    message_with_sender = (
        db.query(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .filter(ChatMessage.id == message.id)
        .first()
    )
    
    return ChatMessageResponse.model_validate(message_with_sender)


@router.post("/rooms/{room_id}/members", response_model=ChatRoomMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member_to_group(
    room_id: int,
    data: ChatRoomMemberAdd,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Add a member to a group chat.
    Only group admins can add members.
    """
    member = ChatService.add_member_to_group(
        db=db,
        company_id=current_user.company_id,
        room_id=room_id,
        admin_user_id=current_user.id,
        data=data
    )
    
    # Load user information
    member_with_user = (
        db.query(ChatRoomMember)
        .options(joinedload(ChatRoomMember.user))
        .filter(ChatRoomMember.id == member.id)
        .first()
    )
    
    return ChatRoomMemberResponse.model_validate(member_with_user)


@router.delete("/rooms/{room_id}/members/{user_id}", response_model=MessageResponse)
async def remove_member_from_group(
    room_id: int,
    user_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Remove a member from a group chat.
    Group admins can remove any member.
    Members can remove themselves.
    """
    ChatService.remove_member_from_group(
        db=db,
        company_id=current_user.company_id,
        room_id=room_id,
        admin_user_id=current_user.id,
        member_user_id=user_id
    )
    
    return MessageResponse(
        message="Member removed from group successfully"
    )

