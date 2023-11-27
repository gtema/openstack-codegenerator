#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

from enum import Enum
import logging
from pathlib import Path
from typing import Optional
import yaml

from pydantic import BaseModel, ConfigDict, Field


class CommandTypeEnum(str, Enum):
    List = "list"
    Show = "show"
    Create = "create"
    Delete = "delete"
    Set = "set"
    Action = "action"
    Download = "download"
    Upload = "upload"
    Json = "json"


class SupportedTargets(str, Enum):
    OpenApiSchena = "openapi-schema"
    RustSdk = "rust-sdk"
    RustCli = "rust-cli"


class OperationTargetParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alternative_module_path: Optional[str] = None
    alternative_module_name: Optional[str] = None
    sdk_mod_path: Optional[str] = None
    cli_mod_path: Optional[str] = None
    command_type: Optional[CommandTypeEnum] = None
    command_name: Optional[str] = None
    service_type: Optional[str] = None
    api_version: Optional[str] = None
    request_key: Optional[str] = None
    response_key: Optional[str] = None
    response_list_item_key: Optional[str] = None


class OperationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: str
    spec_file: str = Field(default=None)
    targets: dict[SupportedTargets, OperationTargetParams]


class ResourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    spec_file: str
    api_version: Optional[str] = None
    operations: dict[str, OperationModel]
    extensions: dict[str, dict] = Field(default={})


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resources: dict[str, ResourceModel]
