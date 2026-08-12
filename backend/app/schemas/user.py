from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    username: str
    display_name: str = ""
    email: EmailStr
    phone: str
    department_id: int | None = None
    password: str

    @field_validator("display_name")
    @classmethod
    def default_display_name(cls, v, info):
        if not v:
            return info.data.get("username", "")
        return v


class UserLoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    email: str
    phone: str
    department_id: int | None = None
    department_name: str | None = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserRoleUpdateRequest(BaseModel):
    role: str


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int


class UserCreateRequest(BaseModel):
    username: str
    display_name: str = ""
    email: EmailStr
    phone: str
    department_id: int | None = None
    role: str = "student"
    is_active: bool = True
    password: str

    @field_validator("display_name")
    @classmethod
    def default_display_name(cls, v, info):
        if not v:
            return info.data.get("username", "")
        return v


class UserUpdateRequest(BaseModel):
    username: str | None = None
    display_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    department_id: int | None = None
    role: str | None = None
    is_active: bool | None = None


class UserPasswordResetRequest(BaseModel):
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ProfileUpdateRequest(BaseModel):
    username: str | None = None
    display_name: str | None = None
    email: EmailStr | None = None


class RefreshRequest(BaseModel):
    access_token: str
    refresh_token: str
