from fastapi import APIRouter
from .schemas import ChatRequest, ChatResponse
from .service import generate_reply

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    reply = generate_reply(req.message)
    return {"reply": reply}