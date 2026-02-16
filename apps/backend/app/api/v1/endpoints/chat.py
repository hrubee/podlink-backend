from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import redis
from app.services.chat_manager import manager
from app.services.chat import ChatService
from app.api import deps, auth_deps
from app.models.user import User
import json

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    token: str = None, # Token passed as query param: /ws?token=...
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    try:
        user = auth_deps.get_current_user_ws(db, token)
        user_id = str(user.id)
    except Exception as e:
        await websocket.close(code=1008) # Policy Violation
        return

    await manager.connect(user_id, websocket)
    chat_service = ChatService(db, r)
    
    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Format expected: {"receiver_id": "...", "content": "..."}
            if "receiver_id" in message_data and "content" in message_data:
                try:
                    await chat_service.send_message(
                        sender_id=user_id,
                        receiver_id=message_data["receiver_id"],
                        content=message_data["content"]
                    )
                except ValueError as ve:
                    # Send error back to client
                    await websocket.send_json({"type": "error", "message": str(ve)})
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception as e:
        print(f"WebSocket Error: {e}")
        manager.disconnect(user_id, websocket)

@router.get("/history/{other_user_id}")
async def get_chat_history(
    other_user_id: str, 
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db)
):
    from app.models.chat import ChatMessage
    current_user_id = str(current_user.id)
    room_id = "-".join(sorted([current_user_id, other_user_id]))
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.room_id == room_id
    ).order_by(ChatMessage.created_at.desc()).limit(50).all()
    
    return messages
