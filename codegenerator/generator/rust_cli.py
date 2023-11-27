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
import copy
from enum import Enum
import logging
from pathlib import Path
import subprocess

from generator.base import BaseGenerator
from generator import common

OPENAPI_RUST_TYPE_MAPPING = {
    "string": {"default": "String"},
    "integer": {"default": "u32", "int32": "u32", "int64": "u64"},
    "number": {"default": "f32", "float": "f32", "double": "f64"},
    "boolean": {"default": "bool"},
    "object": {"default": "HashMap<String, String>"},
}

BASIC_FIELDS = ["id", "name", "created_at", "updated_at"]


class RustCliGenerator(BaseGenerator):
    def __init__(self):
        super().__init__()

    def _format_code(self, *args):
        """Format code using Rustfmt

        :param *args: Path to the code to format
        """
        for path in args:
            subprocess.run(["rustfmt", "--edition", "2021", path])

    def get_parser(self, parser):
        parser.add_argument(
            "--command-type",
            choices=[
                "list",
                "show",
                "create",
                "set",
                "action",
                "delete",
                "download",
                "upload",
                "json",
            ],
            help="Rust CLI Command type (only for rust-cli target)",
        )
        parser.add_argument(
            "--command-name",
            help="Rust CLI Command name (used as final module name)",
        )
        parser.add_argument(
            "--cli-mod-path",
            help="Mod path (dot separated) of the corresponding SDK command (when non standard)",
        )

        parser.add_argument(
            "--sdk-mod-path",
            help="Mod path (dot separated) of the corresponding SDK command (when non standard)",
        )

        return parser

    def _render_command(
        self,
        context: dict,
        impl_template: str,
        impl_dest: Path,
    ):
        """Render command code"""
        self._render(impl_template, context, impl_dest.parent, impl_dest.name)

    def generate(
        self, res, target_dir, openapi_spec=None, operation_id=None, args=None
    ):
        """Generate code for the Rust openstack_cli"""
        logging.debug(
            "Generating Rust CLI code for `%s` in %s"
            % (operation_id, target_dir)
        )

        if not openapi_spec:
            openapi_spec = common.get_openapi_spec(args.openapi_yaml_spec)
        if not operation_id:
            operation_id = args.openapi_operation_id

        (path, method, spec) = common.find_openapi_operation(
            openapi_spec, operation_id
        )
        srv_name, res_name = res.split(".") if res else (None, None)
        # Determine the operation type
        operation_type = (
            args.command_type.value
            if isinstance(args.command_type, Enum)
            else args.command_type or spec.get("x-openstack-operation-type")
        )

        # params = {}
        header_params = {}
        query_params = {}
        path_params = {}
        body_params = {}
        patch_params = {}
        path_elements = [el[1:-1] for el in path.split("/") if el[0:1] == "{"]
        additional_imports = set()

        # original_class_name = "".join(x.title() for x in operation_id.split(".")[0].split("_"))
        original_class_name = operation_id.split(".")[0]
        target_class_name = args.alternative_target_name or original_class_name
        sdk_mod_path = None
        if args.sdk_mod_path is not None:
            sdk_mod_path = [
                args.service_type.replace("-", "_"),
                args.api_version,
            ]
            sdk_mod_path.extend(args.sdk_mod_path.split("::"))
        else:
            sdk_mod_path = common.get_rust_sdk_mod_path(
                args.service_type,
                args.api_version,
                args.alternative_target_name or path,
            )
            sdk_mod_path.append(method)
        cli_mod_path = [
            args.service_type.replace("-", "_"),
            args.api_version,
        ]

        # Collect parameters
        for param in openapi_spec["paths"][path].get(
            "parameters", []
        ) + spec.get("parameters", []):
            (xparam, setter) = common.get_rust_param_dict(param, "cli")
            if xparam:
                if xparam["location"] == "header":
                    header_params[xparam["name"]] = xparam
                if xparam["location"] == "path":
                    xparam["path_position"] = path_elements.index(
                        xparam["name"]
                    )
                    # for i.e. routers/{router_id} we want local_name to be `id` and not `router_id`
                    if xparam["name"] == f"{res_name}_id":
                        xparam["name"] = "id"
                        xparam["local_name"] = "id"

                    path_params[xparam["name"]] = xparam
                if xparam["location"] == "query":
                    query_params[xparam["name"]] = xparam

                additional_imports.update(xparam["additional_imports"])

        # Collect request information
        request_body = spec.get("requestBody")
        body_types = []
        if request_body:
            content = request_body.get("content", {})
            # collect registered media types
            body_types = list(content.keys())
            json_body_schema = content.get("application/json", {}).get(
                "schema"
            )
            if json_body_schema:
                response_def, _ = common.find_resource_schema(
                    json_body_schema, None
                )
                if not response_def:
                    # If there is no "x-openstack-client-resource" down the
                    # pipe take what we have
                    response_def = json_body_schema

                if response_def.get("type") == "object":
                    # Our TL element is an object. This is what we expected
                    required_props = response_def.get("required", [])
                    for k, el in response_def.get("properties", {}).items():
                        (
                            xparam,
                            setter,
                            subtype,
                        ) = common.get_rust_body_element_dict(
                            k, el, k in required_props, "cli-request"
                        )

                        if xparam:
                            body_params[xparam["name"]] = xparam
                            additional_imports.update(
                                xparam.get("additional_imports", set())
                            )

        result_def = {}
        resource_header_metadata = {}

        # Prepare information about response
        if method.upper() != "HEAD":
            for code, rspec in spec["responses"].items():
                if not code.startswith("2"):
                    continue
                content = rspec.get("content", {})
                if "application/json" in content:
                    response_spec = content["application/json"]
                    response_def, _ = common.find_resource_schema(
                        response_spec["schema"], None
                    )
                    if not response_def:
                        continue

                    if response_def["type"] == "object":
                        for k, v in response_def["properties"].items():
                            try:
                                (
                                    xparam,
                                    setter,
                                    subtype,
                                ) = common.get_rust_body_element_dict(
                                    k,
                                    v,
                                    k in response_def.get("required", []),
                                    "cli",
                                )

                                if xparam:
                                    if operation_type == "list" and (
                                        k.lower() not in BASIC_FIELDS
                                        and xparam["local_name"].lower()
                                        not in BASIC_FIELDS
                                    ):
                                        xparam["param_structable_args"].append(
                                            "wide"
                                        )

                                    #                                    params[xparam["name"]] = xparam
                                    field_res = copy.deepcopy(xparam)
                                    field_res["type"] == field_res[
                                        "type"
                                    ].replace("Vec<String>", "VecString")
                                    # Vec<String> in the res must be VecString
                                    if "Vec<String>" in field_res["type"]:
                                        field_res["type"] = field_res[
                                            "type"
                                        ].replace("Vec<String>", "VecString")
                                        additional_imports.add(
                                            "crate::common::VecString"
                                        )
                                    # Vec<Value> in the res must be VecValue
                                    if "Vec<Value>" in field_res["type"]:
                                        field_res["type"] = field_res[
                                            "type"
                                        ].replace("Vec<Value>", "VecValue")
                                        additional_imports.add(
                                            "crate::common::VecValue"
                                        )
                                    # HashMap<String, String> in the res must be HashMapStringString
                                    if (
                                        "HashMap<String, String>"
                                        in field_res["type"]
                                    ):
                                        field_res["type"] = field_res[
                                            "type"
                                        ].replace(
                                            "HashMap<String, String>",
                                            "HashMapStringString",
                                        )
                                        additional_imports.add(
                                            "crate::common::HashMapStringString"
                                        )

                                    result_def[field_res["name"]] = field_res
                                    additional_imports.update(
                                        field_res.get(
                                            "additional_imports", set()
                                        )
                                    )

                                    if method == "patch" and not v.get(
                                        "readOnly", False
                                    ):
                                        field_arg = copy.deepcopy(xparam)
                                        field_arg["location"] = "patch"
                                        patch_params[
                                            field_arg["name"]
                                        ] = field_arg

                            except Exception as ex:
                                raise ValueError(
                                    "Cannot interpret %s in rust: %s" % (k, ex)
                                )

                    else:
                        raise ValueError("Cannot find result object")
        else:
            responses = spec["responses"]
            rspec = None
            # Even though in HEAD case only 204 makes sense Swift object.head
            # returns 200. Therefore try whatever we find first.
            for code in ["204", "200"]:
                if code in responses:
                    rspec = responses[code]
                    break
            for name, hspec in rspec["headers"].items():
                resource_header_metadata[name] = dict(
                    description=hspec.get("description"),
                    type=common.OPENAPI_RUST_TYPE_MAPPING[
                        hspec["schema"]["type"]
                    ]["default"],
                )

        additional_imports.add(
            "openstack_sdk::api::" + "::".join(sdk_mod_path)
        )
        if not args.cli_mod_path:
            cli_mod_path.append(target_class_name)
        else:
            cli_mod_path.extend(args.cli_mod_path.split("::"))

        if method == "patch":
            additional_imports.update(
                [
                    "json_patch::{Patch, diff}",
                    "serde_json::to_value",
                    "openstack_sdk::api::find",
                    (
                        "openstack_sdk::api::"
                        + "::".join(sdk_mod_path[0:-1])
                        + "::find"
                    ),
                ]
            )
        if operation_type in ["set", "unset"] and header_params:
            # When command is set and API accepts headers we add explicit
            # "property" arg
            additional_imports.add("crate::common::parse_key_val")

        if "id" in path_params and operation_type != "list":
            additional_imports.update(
                [
                    "openstack_sdk::api::find",
                    (
                        "openstack_sdk::api::"
                        + "::".join(sdk_mod_path[0:3])
                        + "::find"
                    ),
                ]
            )

        if operation_type == "list":
            # Make plural form for listing
            if target_class_name[-1] == "y":
                target_class_name = target_class_name[0:-1] + "ies"
            elif target_class_name[-1] != "s":
                target_class_name += "s"
            additional_imports.update(
                ["openstack_sdk::api::{paged, Pagination}"]
            )
        if operation_type == "download":
            additional_imports.add("crate::common::download_file")
        if operation_type == "upload":
            additional_imports.add("crate::common::build_upload_asyncread")
        if result_def:
            additional_imports.add("openstack_sdk::api::QueryAsync")
        else:
            additional_imports.add("openstack_sdk::api::RawQueryAsync")

        if resource_header_metadata:
            additional_imports.add("crate::common::HashMapStringString")
            additional_imports.add("std::collections::HashMap")
            if (
                len([x for x in resource_header_metadata.keys() if "*" in x])
                > 0
            ):
                additional_imports.add("regex::Regex")

        if path_params:
            p = sorted(path_params.values(), key=lambda d: d["path_position"])
            last_path_parameter = p[-1]
        else:
            last_path_parameter = None

        context = dict(
            operation_id=operation_id,
            operation_type=operation_type,
            command_description=spec.get("description"),
            # target_class_name=target_class_name.title().replace("_", ""),
            target_class_name="".join(
                x.title() for x in target_class_name.split("_")
            ),
            sdk_struct_name="".join(
                x.title() for x in original_class_name.split("_")
            ),
            # sdk_service_name=args.service_type,
            sdk_service_name=common.get_rust_service_type_from_str(
                args.service_type
            ),
            url=path[1:] if path.startswith("/") else path,
            method=method,
            path_params=path_params,
            query_params=query_params,
            header_params=header_params,
            body_params=body_params,
            patch_params=patch_params,
            resource_key=None,
            resource_header_metadata=resource_header_metadata,
            sdk_mod_path=sdk_mod_path,
            cli_mod_path=cli_mod_path,
            result_def=result_def,
            last_path_parameter=last_path_parameter["name"]
            if last_path_parameter
            else None,
            body_types=body_types,
            additional_imports=additional_imports,
        )

        work_dir = Path(target_dir, "rust", "openstack_cli", "src")
        if not args.cli_mod_path:
            command_name = args.command_name or operation_type
            impl_path = Path(
                work_dir, "/".join(cli_mod_path), f"{command_name}.rs"
            )
        else:
            impl_path = Path(
                work_dir,
                "/".join(cli_mod_path[0:-1]),
                f"{cli_mod_path[-1]}.rs",
            )

        self._render_command(
            context,
            "rust_cli/impl.rs.j2",
            impl_path,
        )

        self._format_code(impl_path)
