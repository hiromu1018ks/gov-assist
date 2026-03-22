"""Shared FastAPI dependencies — extracted from main.py to avoid circular imports."""
import os
import hmac

from fastapi import Depends, HTTPException, Request

# --- Auth disabled for localhost MVP ---
# To re-enable: uncomment get_app_token() and verify_token() below,
# then uncomment Depends(verify_token) in all routers.
#
# def get_app_token() -> str:
#     """Retrieve the APP_TOKEN from environment."""
#     return os.getenv("APP_TOKEN", "")
#
#
# async def verify_token(request: Request, app_token: str = Depends(get_app_token)) -> str:
#     """Validate Bearer token from Authorization header.
#
#     Used as a FastAPI dependency: `Depends(verify_token)`.
#     Returns the validated token string on success.
#     Raises HTTPException on failure.
#     """
#     auth_header = request.headers.get("Authorization")
#     if not auth_header or not auth_header.startswith("Bearer "):
#         raise HTTPException(status_code=401, detail="認証トークンが不足しています")
#
#     token = auth_header[7:]  # Skip "Bearer " prefix (7 chars)
#
#     if not app_token:
#         raise HTTPException(
#             status_code=500,
#             detail="サーバー設定が不完全です（APP_TOKEN未設定）",
#         )
#
#     if not hmac.compare_digest(token, app_token):
#         raise HTTPException(status_code=401, detail="認証トークンが一致しません")
#
#     return token
