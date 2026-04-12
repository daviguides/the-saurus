from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "assistant-ws"}


@router.get("/config")
async def config():
    from assistant_ws.config import settings

    return {
        "llm_provider": settings.llm_provider,
        "llm_model_id": settings.llm_model_id,
    }
