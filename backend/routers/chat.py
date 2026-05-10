from fastapi import APIRouter
from backend.schemas import (
    ChatRequest, ChatResponse, ChatHistoryResponse, ChatMessage
)
from backend.services.chat_service import ChatService

router = APIRouter()
_chat_service = ChatService()


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = _chat_service.process(req.message)
    return result


@router.get("/history", response_model=ChatHistoryResponse)
async def chat_history():
    return ChatHistoryResponse(messages=_chat_service.get_history())
