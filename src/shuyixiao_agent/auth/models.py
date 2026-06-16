"""认证 API 数据模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    """修改密码请求。"""

    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class UserPublic(BaseModel):
    """可返回给前端的用户信息。"""

    id: str
    username: str
    display_name: str
    role: str
    is_active: bool
    must_change_password: bool


class AuthResponse(BaseModel):
    """登录响应。"""

    success: bool
    user: UserPublic
    csrf_token: str


class CurrentUserResponse(BaseModel):
    """当前用户响应。"""

    success: bool
    user: UserPublic


class SuccessResponse(BaseModel):
    """通用成功响应。"""

    success: bool
    message: str
