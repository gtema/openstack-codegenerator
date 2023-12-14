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
import re
import subprocess
from typing import Type, Any

from codegenerator.base import BaseGenerator
from codegenerator import common
from codegenerator import model
from codegenerator.common import BasePrimitiveType
from codegenerator.common import BaseCompoundType
from codegenerator.common import rust as common_rust


class String(BasePrimitiveType):
    lifetimes: set[str] = set(["'a"])
    imports: set[str] = set(["std::borrow::Cow"])
    builder_macros: set[str] = set(["setter(into)"])

    @property
    def type_hint(self):
        return "Cow<'a, str>"

    def get_sample(self):
        return '"foo"'


class Enum(common_rust.Enum):
    @property
    def builder_macros(self):
        macros: set[str] = set(["setter(into)"])
        return macros

    @property
    def builder_container_macros(self):
        return ""

    @property
    def serde_container_macros(self):
        return "#[serde(untagged)]"

    @property
    def derive_container_macros(self):
        return "#[derive(Debug, Deserialize, Clone, Serialize)]"

    def get_sample(self):
        first_kind_name = list(self.kinds.keys())[0]
        first_kind_val = list(self.kinds.values())[0]
        res = (
            self.name
            + "::"
            + first_kind_name
            + "("
            + first_kind_val.data_type.get_sample()
            + (
                ".into()"
                if isinstance(first_kind_val.data_type, String)
                else ""
            )
            + ")"
        )
        return res


class StructField(common_rust.StructField):
    @property
    def builder_macros(self):
        macros: set[str] = set([])
        if not isinstance(self.data_type, BaseCompoundType):
            macros.update(self.data_type.builder_macros)
        elif not isinstance(self.data_type, common_rust.StringEnum):
            macros.add("setter(into)")
        if "private" in macros:
            macros.add(f'setter(name="_{self.local_name}")')
        if self.is_optional:
            macros.add("default")
        return f"#[builder({', '.join(sorted(macros))})]"

    @property
    def serde_macros(self):
        macros = set([])
        if self.local_name != self.remote_name:
            macros.add(f'rename="{self.remote_name}"')
        if self.is_optional:
            macros.add('skip_serializing_if = "Option::is_none"')
        return f"#[serde({', '.join(sorted(macros))})]"


class Struct(common_rust.Struct):
    # field_type_class_ = StructField
    field_type_class_: Type[StructField] | StructField = StructField

    @property
    def derive_container_macros(self):
        return "#[derive(Builder, Debug, Deserialize, Clone, Serialize)]"

    @property
    def builder_container_macros(self):
        return "#[builder(setter(strip_option))]"

    @property
    def serde_container_macros(self):
        return ""

    @property
    def static_lifetime(self):
        """Return Rust `<'lc>` lifetimes representation"""
        return f"<{', '.join(self.lifetimes)}>" if self.lifetimes else ""

    def get_sample(self):
        res = [self.name + "Builder::default()"]
        for field in self.fields.values():
            if not field.is_optional:
                data = f".{field.local_name}("
                data += field.data_type.get_sample()
                data += ")"
                res.append(data)
        res.append(".build().unwrap()")
        return "".join(res)

    def get_mandatory_init(self):
        res = []
        for field in self.fields.values():
            if not field.is_optional:
                data = f".{field.local_name}("
                data += field.data_type.get_sample()
                data += ")"
                res.append(data)
        return "".join(res)


class BTreeMap(common_rust.Dictionary):
    builder_macros: set[str] = set(["private"])
    requires_builder_private_setter: bool = True

    @property
    def type_hint(self):
        return f"BTreeMap<Cow<'a, str>, {self.value_type.type_hint}>"

    @property
    def imports(self):
        imports = set(["std::collections::BTreeMap"])
        imports.update(self.value_type.imports)
        return imports

    @property
    def lifetimes(self):
        lt = set(["'a"])
        if self.value_type.lifetimes:
            lt.update(self.value_type.lifetimes)
        return lt

    # def get_sample(self):
    #    return "BTreeSet::new()"


class CommaSeparatedList(common_rust.CommaSeparatedList):
    @property
    def builder_macros(self):
        return set()


class RequestParameter(common_rust.RequestParameter):
    """OpenAPI request parameter in the Rust SDK form"""

    @property
    def builder_macros(self):
        macros = self.data_type.builder_macros
        macros.add("default")
        if self.setter_name:
            macros.add(f'setter(name="_{self.setter_name}")')
            macros.add("private")
            macros.remove("setter(into)")
        return f"#[builder({', '.join(macros)})]"


class TypeManager(common_rust.TypeManager):
    """Rust SDK type manager

    The class is responsible for converting ADT models into types suitable
    for Rust (SDK).

    """

    primitive_type_mapping: dict[Type[model.PrimitiveType], Type[Any]] = {
        model.PrimitiveString: String,
        model.ConstraintString: String,
    }

    data_type_mapping = {
        model.Dictionary: BTreeMap,
        model.Enum: Enum,
        model.Struct: Struct,
        model.CommaSeparatedList: CommaSeparatedList,
    }

    request_parameter_class: Type[
        common_rust.RequestParameter
    ] = RequestParameter


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
            "Generating Rust SDK code for %s in %s [%s]",
            operation_id,
            target_dir,
            args,
        )

        if not openapi_spec:
            openapi_spec = common.get_openapi_spec(args.openapi_yaml_spec)
        if not operation_id:
            operation_id = args.openapi_operation_id
        (path, method, spec) = common.find_openapi_operation(
            openapi_spec, operation_id
        )
        srv_name, res_name = res.split(".") if res else (None, None)
        # path_resources = common.get_resource_names_from_url(path)
        # res_name = path_resources[-1]

        mime_type = None
        openapi_parser = model.OpenAPISchemaParser()
        operation_params: list[model.RequestParameter] = []
        type_manager: TypeManager | None = None
        # Collect all operation parameters
        for param in openapi_spec["paths"][path].get(
            "parameters", []
        ) + spec.get("parameters", []):
            operation_params.append(openapi_parser.parse_parameter(param))

        # Process body information
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
                    # For action we should come here with operation_type="action" and operation_name must be the action name
                    # For microversions we build body as enum
                    # So now try to figure out what the discriminator is
                    discriminator = json_body_schema.get(
                        "x-openstack", {}
                    ).get("discriminator")
                    if discriminator == "microversion":
                        logging.debug("Microversion discriminator for bodies")
                        for variant in json_body_schema["oneOf"]:
                            variant_spec = variant.get("x-openstack", {})
                            operation_variants.append({"body": variant})
                        # operation_variants.extend([{"body": x} for x in json_body_schema(["oneOf"])])
                    elif discriminator == "action":
                        # We are in the action. Need to find matching body
                        for variant in json_body_schema["oneOf"]:
                            variant_spec = variant.get("x-openstack", {})
                            if (
                                variant_spec.get("action-name")
                                == args.operation_name
                            ):
                                operation_variants.append(
                                    {
                                        "body": variant,
                                        "mode": "action",
                                        "min-ver": variant_spec.get("min-ver"),
                                    }
                                )
                                break
                        if not operation_variants:
                            raise RuntimeError(
                                "Cannot find body specification for action %s"
                                % args.operation_name
                            )
                else:
                    operation_variants.append({"body": json_body_schema})
        else:
            # Explicitly register variant without body
            operation_variants.append({"body": None})

        # jsonschema_parser = model.JsonSchemaParser()
        for operation_variant in operation_variants:
            logging.debug("Processing variant %s" % operation_variant)
            # TODO(gtema): if we are in MV variants filter out unsupported query
            # parameters
            # TODO(gtema): previously we were ensuring `router_id` path param
            # is renamed to `id`

            class_name = res_name.title()
            operation_body = operation_variant.get("body")
            type_manager = TypeManager()
            type_manager.set_parameters(operation_params)
            mod_name = "_".join(
                x.lower()
                for x in re.split(
                    common.SPLIT_NAME_RE,
                    (
                        args.module_name
                        or args.operation_name
                        or args.operation_type.value
                        or method
                    ),
                )
            )

            if operation_body:
                min_ver = operation_body.get("x-openstack", {}).get("min-ver")
                if min_ver:
                    mod_name += "_" + min_ver.replace(".", "")
                # There is request body. Get the ADT from jsonschema
                if args.operation_type != "action":
                    (_, all_types) = openapi_parser.parse(operation_body)
                    # and feed them into the TypeManager
                    type_manager.set_models(all_types)
                    for k, v in type_manager.refs.items():
                        if "BootIndex" in k.name:
                            print("")
                            print(f"{k} => {v}")
                else:
                    logging.warn("Ignoring response type of action")

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
                        try:
                            (
                                response_def,
                                response_key,
                            ) = common.find_resource_schema(
                                response_spec["schema"],
                                None,
                                resource_name=res_name.lower(),
                            )
                        except Exception:
                            # Most likely we have response which is oneOf.
                            # For the SDK it does not really harm to ignore
                            # this.
                            pass
                            # response_def = (None,)
                            response_key = None

            context = dict(
                operation_id=operation_id,
                operation_type=spec.get(
                    "x-openstack-operation-type", args.operation_type
                ),
                command_description=spec.get("description"),
                class_name=class_name,
                sdk_service_name=common.get_rust_service_type_from_str(
                    args.service_type
                ),
                url=path[1:] if path.startswith("/") else path,
                method=method,
                type_manager=type_manager,
                response_key=args.response_key or response_key,
                response_list_item_key=args.response_list_item_key,
                mime_type=mime_type,
            )

            work_dir = Path(target_dir, "rust", "openstack_sdk", "src")
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
