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
from codegenerator.common import BaseCompoundType
from codegenerator.common import rust as common_rust


class String(common_rust.String):
    lifetimes: set[str] = set(["'a"])
    type_hint: str = "Cow<'a, str>"

    @property
    def imports(self) -> set[str]:
        return set(["std::borrow::Cow"])


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
        (first_kind_name, first_kind_val) = list(sorted(self.kinds.items()))[0]
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
            default_set: bool = False
            for macro in macros:
                if "default" in macro:
                    default_set = True
                    break
            if not default_set:
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
    def builder_macros(self):
        return set()

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
        for field in sorted(self.fields.values(), key=lambda d: d.local_name):
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
            if not isinstance(field.data_type, common_rust.Null):
                if not field.is_optional:
                    el = field.data_type.get_sample()
                    if el:
                        data = f".{field.local_name}("
                        data += el
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

    def get_sample(self):
        if isinstance(self.value_type, common_rust.Option):
            return (
                "BTreeMap::<String, Option<String>>::new().into_iter()"
                ".map(|(k, v)| (k, v.map(Into::into)))"
            )
        else:
            return "BTreeMap::<String, String>::new().into_iter()"

    def get_mandatory_init(self):
        return ""


class BTreeSet(common_rust.BTreeSet):
    builder_macros: set[str] = set(["private"])
    requires_builder_private_setter: bool = True


class CommaSeparatedList(common_rust.CommaSeparatedList):
    @property
    def builder_macros(self):
        return set()

    @property
    def imports(self):
        imports: set[str] = set([])
        imports.add("crate::api::common::CommaSeparatedList")
        imports.update(self.item_type.imports)
        return imports


class RequestParameter(common_rust.RequestParameter):
    """OpenAPI request parameter in the Rust SDK form"""

    @property
    def builder_macros(self):
        macros = self.data_type.builder_macros
        macros.add("default")
        if self.setter_name:
            macros.add(f'setter(name="_{self.setter_name}")')
            macros.add("private")
            macros.discard("setter(into)")
        return f"#[builder({', '.join(sorted(macros))})]"


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

    request_parameter_class: Type[common_rust.RequestParameter] = (
        RequestParameter
    )

    def set_parameters(self, parameters: list[model.RequestParameter]) -> None:
        """Set OpenAPI operation parameters into typemanager for conversion"""
        super().set_parameters(parameters)
        for k, param in self.parameters.items():
            if isinstance(param.data_type, common_rust.CommaSeparatedList):
                param.setter_name = param.local_name
                param.setter_type = "csv"
            elif isinstance(param.data_type, common_rust.BTreeSet):
                param.setter_name = param.local_name
                param.setter_type = "set"
            elif isinstance(param.data_type, common_rust.Array):
                param.setter_name = param.local_name
                param.setter_type = "list"
            self.parameters[k] = param


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
        if args.operation_type == "find":
            yield self.generate_find_mod(
                target_dir,
                args.sdk_mod_path.split("::"),
                res.split(".")[-1],
                args.name_field,
                args.list_mod,
                openapi_spec,
                path,
                method,
                spec,
                args.name_filter_supported,
            )
            return

        # srv_name, res_name = res.split(".") if res else (None, None)
        path_resources = common.get_resource_names_from_url(path)
        res_name = path_resources[-1]

        mime_type = None
        openapi_parser = model.OpenAPISchemaParser()
        operation_params: list[model.RequestParameter] = []
        type_manager: TypeManager | None = None
        is_json_patch: bool = False
        # Collect all operation parameters
        for param in openapi_spec["paths"][path].get(
            "parameters", []
        ) + spec.get("parameters", []):
            if (
                ("{" + param["name"] + "}") in path and param["in"] == "path"
            ) or param["in"] != "path":
                # Respect path params that appear in path and not path params
                param_ = openapi_parser.parse_parameter(param)
                if param_.name == f"{res_name}_id":
                    path = path.replace(f"{res_name}_id", "id")
                    # for i.e. routers/{router_id} we want local_name to be `id` and not `router_id`
                    param_.name = "id"
                operation_params.append(param_)

        # Process body information
        # List of operation variants (based on the body)
        operation_variants = common.get_operation_variants(
            spec, args.operation_name
        )

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
                # if args.operation_type != "action":
                (_, all_types) = openapi_parser.parse(
                    operation_body, ignore_read_only=True
                )
                # and feed them into the TypeManager
                type_manager.set_models(all_types)
                # else:
                #    logging.warn("Ignoring response type of action")

            if method == "patch":
                # There might be multiple supported mime types. We only select ones we are aware of
                mime_type = operation_variant.get("mime_type")
                if not mime_type:
                    raise RuntimeError(
                        "No supported mime types for patch operation found"
                    )
                if mime_type != "application/json":
                    is_json_patch = True

            mod_path = common.get_rust_sdk_mod_path(
                args.service_type,
                args.api_version,
                args.alternative_module_path or path,
            )

            response_key: str | None = None
            if args.response_key:
                response_key = (
                    args.response_key if args.response_key != "null" else None
                )
            else:
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
                                    _,
                                    response_key,
                                ) = common.find_resource_schema(
                                    response_spec["schema"],
                                    None,
                                    res_name.lower(),
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
                command_description=common.make_ascii_string(
                    spec.get("description")
                ),
                class_name=class_name,
                sdk_service_name=common.get_rust_service_type_from_str(
                    args.service_type
                ),
                url=path[1:] if path.startswith("/") else path,
                method=method,
                type_manager=type_manager,
                response_key=response_key,
                response_list_item_key=args.response_list_item_key,
                mime_type=mime_type,
                is_json_patch=is_json_patch,
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
        """Generate collection module (include individual modules)"""
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

    def generate_find_mod(
        self,
        target_dir,
        mod_path,
        resource_name,
        name_field: str,
        list_mod: str,
        openapi_spec,
        path: str,
        method: str,
        spec,
        name_filter_supported: bool = False,
    ):
        """Generate `find` operation module"""
        work_dir = Path(target_dir, "rust", "openstack_sdk", "src")
        impl_path = Path(
            work_dir,
            "api",
            "/".join(mod_path),
            "find.rs",
        )
        # Collect all operation parameters
        openapi_parser = model.OpenAPISchemaParser()
        path_resources = common.get_resource_names_from_url(path)
        res_name = path_resources[-1]
        operation_path_params: list[model.RequestParameter] = []
        operation_query_params: list[model.RequestParameter] = []

        for param in openapi_spec["paths"][path].get(
            "parameters", []
        ) + spec.get("parameters", []):
            if ("{" + param["name"] + "}") in path and param["in"] == "path":
                # Respect path params that appear in path and not in path params
                param_ = openapi_parser.parse_parameter(param)
                if param_.name == f"{res_name}_id":
                    path = path.replace(f"{res_name}_id", "id")
                    # for i.e. routers/{router_id} we want local_name to be `id` and not `router_id`
                    param_.name = "id"
                operation_path_params.append(param_)
            if param["in"] == "query":
                # Capture query params to estimate lifetime of the operation
                operation_query_params.append(param)
        type_manager = TypeManager()
        type_manager.set_parameters(operation_path_params)

        context = dict(
            mod_path=mod_path,
            resource_name=resource_name,
            list_mod=list_mod,
            name_filter_supported=name_filter_supported,
            name_field=name_field,
            type_manager=type_manager,
            list_lifetime=(
                "<'a>"
                if operation_query_params or operation_path_params
                else ""
            ),
        )

        # Generate methods for the GET resource command
        self._render_command(
            context,
            "rust_sdk/find.rs.j2",
            impl_path,
        )

        self._format_code(impl_path)

        return (mod_path, "find", "dummy")
