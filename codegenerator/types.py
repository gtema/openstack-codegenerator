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

from pydantic import BaseModel, ConfigDict, Field


class CommandTypeEnum(str, Enum):
    """Supported Command/Operation types"""

    List = "list"
    # fetch resource by name
    Show = "show"
    # general GET operation
    Get = "get"
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
    # deprecated
    alternative_module_path: str | None = None
    module_path: str | None = None
    # deprecated
    alternative_module_name: str | None = None
    module_name: str | None = None
    sdk_mod_path: str | None = None
    sdk_mod_name: str | None = None
    cli_mod_path: str | None = None
    operation_type: CommandTypeEnum | None = None
    # currently used for actions to find proper response body
    operation_name: str | None = None
    service_type: str | None = None
    api_version: str | None = None
    request_key: str | None = None
    response_key: str | None = None
    response_list_item_key: str | None = None


class OperationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: str
    spec_file: str = Field(default=None)
    operation_type: CommandTypeEnum | None = None
    targets: dict[SupportedTargets, OperationTargetParams]


class ResourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    spec_file: str
    api_version: str | None = None
    operations: dict[str, OperationModel]
    extensions: dict[str, dict] = Field(default={})


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resources: dict[str, ResourceModel]
