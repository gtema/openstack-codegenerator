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

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


OPERATION_TYPE = Literal[
    "list",
    "show",
    "get",
    "create",
    "delete",
    "set",
    "action",
    "download",
    "upload",
    "json",
    "find",
]

SUPPORTED_TARGETS = Literal["rust-sdk", "rust-cli"]


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
    operation_type: OPERATION_TYPE | None = None
    # currently used for actions to find proper response body
    operation_name: str | None = None
    service_type: str | None = None
    api_version: str | None = None
    request_key: str | None = None
    response_key: str | None = None
    response_list_item_key: str | None = None
    #: Flag indicating that `find` operation is implemented by the corresponding SDK
    find_implemented_by_sdk: bool | None = None
    #: Name or the resource `name` field
    name_field: str | None = None
    #: Flag whether `name` query parameter to the `list` method is supported.
    #: Used by SDK to implement `find` method.
    name_filter_supported: bool | None = None
    #: List module for the find
    list_mod: str | None = None


class OperationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: str
    spec_file: str = Field(default=None)
    operation_type: OPERATION_TYPE | None = None
    targets: dict[SUPPORTED_TARGETS, OperationTargetParams]


class ResourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    spec_file: str
    api_version: str | None = None
    operations: dict[str, OperationModel]
    extensions: dict[str, dict] = Field(default={})


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resources: dict[str, ResourceModel]
