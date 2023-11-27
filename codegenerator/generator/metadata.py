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
import pathlib
import json
import logging

from generator.base import BaseGenerator
from generator.common.schema import SpecSchema
from generator.common import get_resource_names_from_url
from generator.types import Metadata
from generator.types import OperationModel
from generator.types import OperationTargetParams
from generator.types import ResourceModel
from ruamel.yaml import YAML


class MetadataGenerator(BaseGenerator):
    """Generate metadata from OpenAPI spec"""

    def load_openapi(self, path):
        """Load existing OpenAPI spec from the file"""
        if not path.exists():
            return
        yaml = YAML(typ="safe")
        with open(path, "r") as fp:
            spec = yaml.load(fp)

        return SpecSchema(**spec)

    def generate(
        self, res, target_dir, openapi_spec=None, operation_id=None, args=None
    ):
        """Generate Json Schema definition file for Resource"""
        logging.debug("Generating OpenAPI schema data")
        # We do not import generators since due to the use of Singletons in the
        # code importing glance, nova, cinder at the same time crashes
        # dramatically
        schema = self.load_openapi(pathlib.Path(args.openapi_yaml_spec))
        metadata = Metadata(resources=dict())
        api_ver = "v" + schema.info["version"].split(".")[0]
        for path, spec in schema.paths.items():
            resource_name = "/".join(
                [x for x in get_resource_names_from_url(path)]
            )
            resource_model = metadata.resources.setdefault(
                f"{args.service_type}.{resource_name}",
                ResourceModel(
                    api_version=api_ver,
                    spec_file=args.openapi_yaml_spec,
                    operations=dict(),
                ),
            )
            for method in ["head", "get", "put", "post", "delete", "options"]:
                operation = getattr(spec, method, None)
                if operation:
                    if not operation.operationId:
                        # Every operation must have operationId
                        continue
                    op_model = OperationModel(
                        operation_id=operation.operationId, targets=dict()
                    )
                    operation_name = ""

                    if path.endswith("}"):
                        if method == "get":
                            operation_name = "show"
                        elif method == "put":
                            operation_name = "update"
                        elif method == "delete":
                            operation_name = "delete"
                    elif path.endswith("/detail"):
                        if method == "get":
                            operation_name = "list_detailed"
                    elif path.endswith("/action"):
                        # Action
                        operation_name = "action"
                    elif (
                        len(
                            [
                                x
                                for x in schema.paths.keys()
                                if x.startswith(path + "/{")
                            ]
                        )
                        > 0
                    ):
                        # if we are at i.e. /v2/servers
                        # and there is /v2/servers/{ most
                        # likely we are at the collection
                        # level
                        if method == "get":
                            operation_name = "list"
                        elif method == "post":
                            operation_name = "create"
                        elif method == "put":
                            operation_name = "replace"
                        elif method == "delete":
                            operation_name = "delete_all"
                    elif method == "get":
                        operation_name = "get"
                    elif method == "post":
                        operation_name = "create"
                    elif method == "put":
                        operation_name = path.split("/")[-1]
                    elif method == "delete":
                        operation_name = "delete"
                    if not operation_name:
                        print(f"Cannot identify op name for {path}:{method}")
                    if operation_name in resource_model:
                        raise RuntimeError("Operation name conflict")
                    else:
                        if operation_name == "action":
                            # For action we actually have multiple independent operations
                            try:
                                bodies = operation.requestBody["content"][
                                    "application/json"
                                ]["schema"]["oneOf"]
                                for body in bodies:
                                    print(f"action {body}")
                            except KeyError:
                                raise RuntimeError(
                                    "Cannot get bodies for %s" % path
                                )
                        rust_sdk_params = get_rust_sdk_operation_args(
                            operation_name
                        )

                        # OperationTargetParams()
                        # if operation_name == "list_detailed":
                        #    rust_sdk_params.command_type = "list"
                        # elif operation_name == "get":
                        #    rust_sdk_params.command_type = "show"
                        # elif operation_name in ["update", "replace"]:
                        #    rust_sdk_params.command_type = "set"
                        # elif operation_name in ["delete_all"]:
                        #    rust_sdk_params.command_type = "delete"
                        # else:
                        #    rust_sdk_params.command_type = operation_name
                        # if operation_name != rust_sdk_params.command_type:
                        #    rust_sdk_params.alternative_module_name = (
                        #        operation_name
                        #    )
                        op_model.targets["rust-sdk"] = rust_sdk_params
                        resource_model.operations[operation_name] = op_model
                    pass
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.default_flow_style = False
        yaml.indent(mapping=2, sequence=4, offset=2)
        with open(
            pathlib.Path(target_dir, args.service_type + "_metadata.yaml"), "w"
        ) as fp:
            yaml.dump(
                metadata.model_dump(
                    exclude_none=True, exclude_defaults=True, by_alias=True
                ),
                fp,
            )


def get_rust_sdk_operation_args(operation_name):
    rust_sdk_params = OperationTargetParams()
    if operation_name == "list_detailed":
        rust_sdk_params.command_type = "list"
    elif operation_name == "get":
        rust_sdk_params.command_type = "show"
    elif operation_name in ["update", "replace"]:
        rust_sdk_params.command_type = "set"
    elif operation_name in ["delete_all"]:
        rust_sdk_params.command_type = "delete"
    else:
        rust_sdk_params.command_type = operation_name
    if operation_name != rust_sdk_params.command_type:
        rust_sdk_params.alternative_module_name = operation_name
    # op_model.targets["rust-sdk"] = rust_sdk_params
    return rust_sdk_params
