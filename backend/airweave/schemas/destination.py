"""Destination schema."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from airweave.platform.auth.schemas import AuthType
from airweave.platform.configs._base import Fields


class DestinationBase(BaseModel):
    """Base schema for Destination."""

    name: str
    description: Optional[str] = None
    short_name: str
    class_name: str
    auth_type: Optional[AuthType] = None
    auth_config_class: Optional[str] = None
    input_entity_definition_ids: Optional[List[UUID]] = None
    organization_id: Optional[UUID] = None
    config_schema: Optional[dict] = None
    labels: Optional[List[str]] = None

    class Config:
        """Pydantic config for DestinationBase."""

        from_attributes = True


class DestinationCreate(DestinationBase):
    """Schema for creating a Destination object."""

    pass


class DestinationUpdate(DestinationBase):
    """Schema for updating a Destination object."""

    pass


class DestinationInDBBase(DestinationBase):
    """Base schema for Destination stored in DB."""

    id: UUID
    created_at: datetime
    modified_at: datetime

    class Config:
        """Pydantic config for DestinationInDBBase."""

        from_attributes = True


class Destination(DestinationInDBBase):
    """Schema for Destination."""

    pass


class DestinationWithConfigFields(Destination):
    """Schema for Destination with auth config."""

    config_fields: Fields | None = None
