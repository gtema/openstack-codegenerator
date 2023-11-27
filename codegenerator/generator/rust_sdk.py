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

import logging
from pathlib import Path
import subprocess

from generator.base import BaseGenerator
from generator import common

# from generator.common.schema import RestEndpointSchema

OPENAPI_RUST_TYPE_MAPPING = {
    "string": {"default": "Cow<'a, str>"},
    "integer": {"default": "u32", "int32": "u32", "int64": "u64"},
    "number": {"default": "f32", "float": "f32", "double": "f64"},
    "boolean": {"default": "bool"},
}


class RustSdkGenerator(BaseGenerator):
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
            "--response-key",
            help="Rust SDK response key (only required when normal detection does not work)",
        )

        parser.add_argument(
            "--response-list-item-key",
            help='Rust SDK list response item key (specifies whether list items are wrapped in additional container `{"keypairs":["keypair":{}]}`)',
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
        """Generate code for the Rust openstack_sdk"""
        logging.debug(
            "Generating Rust SDK code for %s in %s"
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
        path_resources = common.get_resource_names_from_url(path)
        res_name = path_resources[-1]
        if path.endswith("action"):
            logging.warn("Skipping action for now")
            return

        params = {}
        param_setters = []
        mime_type = None
        subtypes = {}
        additional_imports = set()
        # Process parameters
        for param in openapi_spec["paths"][path].get(
            "parameters", []
        ) + spec.get("parameters", []):
            (xparam, setter) = common.get_rust_param_dict(param, "sdk")
            if xparam:
                # for i.e. routers/{router_id} we want local_name to be `id` and not `router_id`
                if (
                    xparam["location"] == "path"
                    and xparam["name"] == f"{res_name.lower()}_id"
                ):
                    xparam["local_name"] = "id"
                params[xparam["name"]] = xparam
                additional_imports.update(xparam["additional_imports"])
            if setter:
                param_setters.append(setter)

        # Process body
        request_body = spec.get("requestBody")
        # List of operation variants (based on the body)
        operation_variants = []
        if request_body:
            content = request_body.get("content", {})
            json_body_schema = content.get("application/json", {}).get(
                "schema"
            )
            if json_body_schema:
                mime_type = "application/json"
                # response_def = json_body_schema
                if "oneOf" in json_body_schema:
                    # There is a choice of bodies. It can be because of
                    # microversion or an action (or both)
                    # For action we should come here with command_type="action" and command_name must be the action name
                    # For microversions we build body as enum
                    # So now try to figure out what the discriminator is
                    discriminator = json_body_schema.get(
                        "x-openstack", {}
                    ).get("discriminator")
                    if discriminator == "microversion":
                        logging.debug("Microversion discriminator for bodies")
                        for variant in json_body_schema["oneOf"]:
                            operation_variants.append({"body": variant})
                        # operation_variants.extend([{"body": x} for x in json_body_schema(["oneOf"])])
                else:
                    operation_variants.append({"body": json_body_schema})
        else:
            # Explicitly register variant without body
            operation_variants.append({"body": None})
        for operation_variant in operation_variants:
            print("Processing variant %s" % operation_variant)
            request_key = None
            class_name = res_name.title()
            operation_body = operation_variant.get("body")
            mod_name = (
                args.alternative_module_name
                or args.command_type.value
                or method
            )

            if operation_body:
                try:
                    request_def, request_key = common.find_resource_schema(
                        operation_body, None, resource_name=res_name
                    )
                except Exception:
                    logging.warn("Cannot identity body")
                    return
                min_ver = operation_body.get("x-openstack", {}).get("min-ver")
                if min_ver:
                    mod_name += "_" + min_ver.replace(".", "")
                if not request_def:
                    # Not able to identity where the resource schema is. Take the whole schema as is
                    request_def = json_body_schema

                if request_def.get("type") == "object":
                    # Our TL element is an object. This is what we expected
                    required_props = request_def.get("required", [])
                    for k, el in request_def.get("properties", {}).items():
                        (
                            xparam,
                            setter,
                            xsubtypes,
                        ) = common.get_rust_body_element_dict(
                            k, el, k in required_props, "sdk"
                        )

                        if xparam:
                            params[xparam["name"]] = xparam
                        if xsubtypes:
                            subtypes.update(xsubtypes)
                        if setter:
                            param_setters.append(setter)

                        additional_imports.update(xparam["additional_imports"])
            if method == "patch":
                # There might be multiple supported mime types. We only select ones we are aware of
                if "application/openstack-images-v2.1-json-patch" in content:
                    mime_type = "application/openstack-images-v2.1-json-patch"
                elif "application/json-patch+json" in content:
                    mime_type = "application/json-patch+json"
                else:
                    raise RuntimeError(
                        "No supported mime types for patch operation found"
                    )

            # class_name = "".join(
            #    x.title() for x in operation_id.split(".")[0].split("_")
            # )
            mod_path = common.get_rust_sdk_mod_path(
                args.service_type,
                args.api_version,
                args.alternative_module_path or path,
            )

            response_def = None
            response_key = None
            # Get basic information about response
            if method.upper() != "HEAD":
                for code, rspec in spec["responses"].items():
                    if not code.startswith("2"):
                        continue
                    content = rspec.get("content", {})
                    if "application/json" in content:
                        response_spec = content["application/json"]
                        (
                            response_def,
                            response_key,
                        ) = common.find_resource_schema(
                            response_spec["schema"],
                            None,
                            resource_name=res_name.lower(),
                        )

            context = dict(
                operation_id=operation_id,
                operation_type=spec.get(
                    "x-openstack-operation-type", args.command_type
                ),
                command_description=spec.get("description"),
                class_name=class_name,
                sdk_service_name=common.get_rust_service_type_from_str(
                    args.service_type
                ),
                url=path[1:] if path.startswith("/") else path,
                method=method,
                params=params,
                request_key=args.request_key or request_key,
                response_key=args.response_key or response_key,
                response_list_item_key=args.response_list_item_key,
                path_params={
                    k: v for k, v in params.items() if v["location"] == "path"
                },
                query_params={
                    k: v for k, v in params.items() if v["location"] == "query"
                },
                body_params={
                    k: v for k, v in params.items() if v["location"] == "body"
                },
                static_lifetime=bool(
                    len(
                        list(
                            v
                            for v in params.values()
                            if v["location"] in ["path", "query", "body"]
                            and "'a" in v["type"]
                        )
                    )
                    > 0
                ),
                param_setters=param_setters,
                mime_type=mime_type,
                additional_imports=additional_imports,
                subtypes=subtypes,
            )

            work_dir = Path(target_dir, "rust", "openstack_sdk", "src")
            # mod_name
            impl_path = Path(
                work_dir,
                "api",
                "/".join(mod_path),
                f"{mod_name}.rs",
            )

            # Generate methods for the GET resource command
            self._render_command(
                context,
                "rust_sdk/impl.rs.j2",
                impl_path,
            )

            self._format_code(impl_path)

            yield (mod_path, mod_name, path)

    def generate_mod(
        self, target_dir, mod_path, mod_list, url, resource_name, service_name
    ):
        work_dir = Path(target_dir, "rust", "openstack_sdk", "src")
        impl_path = Path(
            work_dir,
            "api",
            "/".join(mod_path[0:-1]),
            f"{mod_path[-1]}.rs",
        )

        context = dict(
            mod_list=mod_list,
            mod_path=mod_path,
            url=url,
            resource_name=resource_name,
            service_name=service_name,
        )

        # Generate methods for the GET resource command
        self._render_command(
            context,
            "rust_sdk/mod.rs.j2",
            impl_path,
        )

        self._format_code(impl_path)
