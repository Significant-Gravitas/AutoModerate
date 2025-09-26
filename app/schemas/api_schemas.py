"""
Pydantic schemas for API request/response validation
"""
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class ContentType(str, Enum):
    """Allowed content types for moderation"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class ModerationStatus(str, Enum):
    """Moderation decision statuses"""
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"
    PENDING = "pending"


class ModerateContentRequest(BaseModel):
    """Schema for content moderation requests"""
    type: ContentType = Field(default=ContentType.TEXT, description="Type of content to moderate")
    content: str = Field(..., min_length=1, max_length=5000000, description="Content to moderate")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")

    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Content cannot be empty or only whitespace')
        return v.strip()

    @validator('metadata')
    def validate_metadata(cls, v):
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError('Metadata must be a dictionary')
            # Validate metadata keys and values
            for key, value in v.items():
                if not isinstance(key, str) or len(key) > 50:
                    raise ValueError('Metadata keys must be strings with max length 50')
                if isinstance(value, str) and len(value) > 1000:
                    raise ValueError('Metadata string values must be max 1000 characters')
                # Prevent nested objects beyond reasonable depth
                if isinstance(value, (dict, list)) and str(value).count('{') + str(value).count('[') > 10:
                    raise ValueError('Metadata objects too deeply nested')
        return v

    class Config:
        # Allow extra fields but validate defined ones
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "type": "text",
                "content": "This is content to be moderated",
                "metadata": {
                    "user_id": "external_user_123",
                    "source": "user_comment"
                }
            }
        }


class ModerationResultResponse(BaseModel):
    """Schema for moderation result responses"""
    decision: ModerationStatus
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    reason: str
    moderator_type: str = Field(description="Type of moderator (rule|ai|manual)")
    processing_time: float = Field(ge=0.0, description="Processing time in seconds")
    rule_id: Optional[str] = Field(default=None, description="ID of triggered rule if applicable")

    class Config:
        json_schema_extra = {
            "example": {
                "decision": "approved",
                "confidence": 0.95,
                "reason": "Content passed all moderation checks",
                "moderator_type": "rule",
                "processing_time": 0.23,
                "rule_id": "rule_uuid_here"
            }
        }


class ModerateContentResponse(BaseModel):
    """Schema for content moderation API responses"""
    success: bool = True
    content_id: str
    status: ModerationStatus
    moderation_results: list[ModerationResultResponse]
    processing_time: Optional[float] = Field(default=None, ge=0.0)

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "content_id": "content_uuid_here",
                "status": "approved",
                "moderation_results": [
                    {
                        "decision": "approved",
                        "confidence": 0.95,
                        "reason": "Content passed all moderation checks",
                        "moderator_type": "rule",
                        "processing_time": 0.23
                    }
                ]
            }
        }


class ErrorResponse(BaseModel):
    """Schema for API error responses"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Invalid input data",
                "error_code": "VALIDATION_ERROR",
                "details": {
                    "field_errors": ["content field is required"]
                }
            }
        }


class ContentListRequest(BaseModel):
    """Schema for content list requests"""
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=50, ge=1, le=100, description="Items per page")
    status: Optional[ModerationStatus] = Field(default=None, description="Filter by status")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "per_page": 50,
                "status": "approved"
            }
        }


class APIKeyCreateRequest(BaseModel):
    """Schema for API key creation requests"""
    name: str = Field(..., min_length=1, max_length=100, description="Name for the API key")

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('API key name cannot be empty')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Production API Key"
            }
        }


class UserCreateRequest(BaseModel):
    """Schema for user creation requests"""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=6, max_length=100, description="Password")
    is_admin: bool = Field(default=False, description="Admin privileges")
    is_active: bool = Field(default=True, description="Account active status")

    @validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens and underscores')
        return v.strip()

    @validator('email')
    def validate_email(cls, v):
        import re
        if not v or not v.strip():
            raise ValueError('Email cannot be empty')
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Invalid email format')
        return v.strip().lower()

    class Config:
        json_schema_extra = {
            "example": {
                "username": "newuser",
                "email": "user@example.com",
                "password": "securepassword",
                "is_admin": False,
                "is_active": True
            }
        }
