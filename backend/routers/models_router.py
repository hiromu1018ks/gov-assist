"""GET /api/models — 利用可能な AI モデル一覧 (§4.2, §5.1)."""
from fastapi import APIRouter, Depends

from dependencies import verify_token
from schemas import ModelsResponse, ModelInfoResponse
from services.ai_client import MODEL_CONFIGS

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models", response_model=ModelsResponse)
async def get_models(token: str = Depends(verify_token)):
    """Return all available AI models from the model config table."""
    models = [
        ModelInfoResponse(
            model_id=model_id,
            display_name=config.display_name,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            max_input_chars=config.max_input_chars,
            json_forced=config.json_forced,
        )
        for model_id, config in MODEL_CONFIGS.items()
    ]
    return ModelsResponse(models=models)
