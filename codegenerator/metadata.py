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
import logging
import re

from codegenerator.base import BaseGenerator
from codegenerator import common
from codegenerator.common.schema import SpecSchema
from codegenerator.types import Metadata

# from codegenerator.types import CommandTypeEnum
from codegenerator.types import OperationModel
from codegenerator.types import OperationTargetParams
from codegenerator.types import ResourceModel
import jsonref
from ruamel.yaml import YAML


class MetadataGenerator(BaseGenerator):
    """Generate metadata from OpenAPI spec"""

    def load_openapi(self, path):
        """Load existing OpenAPI spec from the file"""
        if not path.exists():
            return
        yaml = YAML(typ="safe")
        with open(path, "r") as fp:
            spec = jsonref.replace_refs(yaml.load(fp))

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
                [x for x in common.get_resource_names_from_url(path)]
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
                    operation_key: str | None = None

                    if path.endswith("}"):
                        if method == "get":
                            operation_key = "show"
                        elif method == "put":
                            operation_key = "update"
                        elif method == "delete":
                            operation_key = "delete"
                    elif path.endswith("/detail"):
                        if method == "get":
                            operation_key = "list_detailed"
                    elif path.endswith("/action"):
                        # Action
                        operation_key = "action"
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
                            operation_key = "list"
                        elif method == "post":
                            operation_key = "create"
                        elif method == "put":
                            operation_key = "replace"
                        elif method == "delete":
                            operation_key = "delete_all"
                    elif method == "get":
                        operation_key = "get"
                    elif method == "post":
                        operation_key = "create"
                    elif method == "put":
                        operation_key = path.split("/")[-1]
                    elif method == "delete":
                        operation_key = "delete"
                    if not operation_key:
                        logging.warn(
                            f"Cannot identify op name for {path}:{method}"
                        )
                    if operation_key in resource_model:
                        raise RuntimeError("Operation name conflict")
                    else:
                        if operation_key == "action":
                            # For action we actually have multiple independent operations
                            try:
                                body_schema = operation.requestBody["content"][
                                    "application/json"
                                ]["schema"]
                                bodies = body_schema["oneOf"]
                                discriminator = body_schema.get(
                                    "x-openstack", {}
                                ).get("discriminator")
                                if discriminator != "action":
                                    raise RuntimeError(
                                        "Cannot generate metadata for %s since requet body is not having action discriminator"
                                        % path
                                    )
                                for body in bodies:
                                    action_name = body.get(
                                        "x-openstack", {}
                                    ).get("action-name")
                                    if not action_name:
                                        action_name = list(
                                            body["properties"].keys()
                                        )[0]
                                    # Hardcode fixes
                                    if (
                                        resource_name == "flavor"
                                        and action_name
                                        in ["update", "create", "delete"]
                                    ):
                                        # Flavor update/create/delete
                                        # operations are exposed ALSO as wsgi
                                        # actions. This is wrong and useless.
                                        logging.warn(
                                            "Skipping generating %s:%s action",
                                            resource_name,
                                            action_name,
                                        )
                                        continue

                                    operation_name = "-".join(
                                        x.lower()
                                        for x in re.split(
                                            common.SPLIT_NAME_RE, action_name
                                        )
                                    ).lower()
                                    rust_sdk_params = (
                                        get_rust_sdk_operation_args(
                                            "action",
                                            operation_name=action_name,
                                            module_name=get_module_name(
                                                action_name
                                            ),
                                        )
                                    )
                                    rust_cli_params = (
                                        get_rust_cli_operation_args(
                                            "action",
                                            operation_name=action_name,
                                            module_name=get_module_name(
                                                action_name
                                            ),
                                        )
                                    )

                                    op_model = OperationModel(
                                        operation_id=operation.operationId,
                                        targets=dict(),
                                    )
                                    op_model.operation_type = (
                                        "action"  # type: ignore
                                    )

                                    op_model.targets[
                                        "rust-sdk"  # type: ignore
                                    ] = rust_sdk_params
                                    op_model.targets[
                                        "rust-cli"  # type: ignore
                                    ] = rust_cli_params
                                    resource_model.operations[
                                        operation_name
                                    ] = op_model

                            except KeyError:
                                raise RuntimeError(
                                    "Cannot get bodies for %s" % path
                                )
                        else:
                            if not operation_key:
                                raise NotImplementedError
                            operation_type = get_operation_type_by_key(
                                operation_key
                            )
                            op_model.operation_type = operation_type
                            # NOTE: sdk gets operation_key and not operation_type
                            rust_sdk_params = get_rust_sdk_operation_args(
                                operation_key
                            )
                            rust_cli_params = get_rust_cli_operation_args(
                                operation_key
                            )

                            op_model.targets["rust-sdk"] = rust_sdk_params  # type: ignore
                            if rust_cli_params:
                                op_model.targets["rust-cli"] = rust_cli_params  # type: ignore
                            resource_model.operations[operation_key] = op_model
                    pass
        for res_name, res_data in metadata.resources.items():
            # Sanitize produced metadata
            list_op = res_data.operations.get("list")
            list_detailed_op = res_data.operations.get("list_detailed")
            if list_op and list_detailed_op:
                # There are both plain list and list with details operation.
                # For the certain generator backend it makes no sense to have
                # then both so we should disable generation of certain backends
                # for the non detailed endpoint
                list_op.targets.pop("rust-cli")  # type: ignore
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


def get_operation_type_by_key(operation_key):
    if operation_key == "list_detailed":
        return "list"
    elif operation_key == "show":
        return "show"
    elif operation_key in ["update", "replace"]:
        return "set"
    elif operation_key in ["delete_all"]:
        return "delete"
    else:
        return operation_key


def get_rust_sdk_operation_args(
    operation_key: str,
    operation_name: str | None = None,
    module_name: str | None = None,
):
    """Construct proper Rust SDK parameters for operation by type"""
    sdk_params = OperationTargetParams()
    sdk_params.module_name = module_name
    if operation_key == "show":
        sdk_params.module_name = "get"
    elif operation_key == "list_detailed":
        sdk_params.module_name = "list_detailed"
    else:
        sdk_params.module_name = module_name or get_module_name(
            get_operation_type_by_key(operation_key)
        )
    sdk_params.operation_name = operation_name

    return sdk_params


def get_rust_cli_operation_args(
    operation_key: str,
    operation_name: str | None = None,
    module_name: str | None = None,
):
    """Construct proper Rust CLI parameters for operation by type"""
    # Get SDK params to connect things with each other
    operation_type = get_operation_type_by_key(operation_key)
    sdk_params = get_rust_sdk_operation_args(
        operation_key, operation_name=operation_name, module_name=module_name
    )
    cli_params = OperationTargetParams()
    cli_params.sdk_mod_name = sdk_params.module_name
    cli_params.module_name = module_name or get_module_name(operation_type)
    cli_params.operation_name = operation_name

    return cli_params


def get_module_name(name):
    return "_".join(x.lower() for x in re.split(common.SPLIT_NAME_RE, name))
