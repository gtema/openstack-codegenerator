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
from typing import Any
import re

import jsonref
import yaml
from openapi_core import Spec

# from pydantic import BaseModel, ConfigDict, Field

# from codegenerator import types

# from codegenerator.model import Types

VERSION_RE = re.compile(r"[Vv][0-9.]*")


def _deep_merge(
    dict1: dict[Any, Any], dict2: dict[Any, Any]
) -> dict[Any, Any]:
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = _deep_merge(result[key], value)
                continue
            elif isinstance(result[key], list) and isinstance(value, list):
                result[key] = result[key] + value
                continue
        result[key] = value
    return result


OPENAPI_RUST_TYPE_MAPPING = {
    "string": {"default": "Cow<'a, str>"},
    "integer": {"default": "u32", "int32": "u32", "int64": "u64"},
    "number": {"default": "f32", "float": "f32", "double": "f64"},
    "boolean": {"default": "bool"},
    "object": {"default": "HashMap<String, String>"},
    # in SDK (most likely means "sending") for string or number just take
    # number
    "intstring": {"default": "u64"},
}

OPENAPI_RUST_CLI_TYPE_MAPPING = {
    "string": {"default": "String"},
    "integer": {"default": "u32", "int32": "u32", "int64": "u64"},
    "number": {"default": "f32", "float": "f32", "double": "f64"},
    "boolean": {"default": "bool"},
    "object": {"default": "HashMap<String, String>"},
    "intstring": {"default": "NumString"},
}

OPENAPI_RUST_CLI_REQUEST_TYPE_MAPPING = {
    "string": {"default": "String"},
    "integer": {"default": "u32", "int32": "u32", "int64": "u64"},
    "number": {"default": "f32", "float": "f32", "double": "f64"},
    "boolean": {"default": "bool"},
    "object": {"default": "HashMap<String, String>"},
    "intstring": {"default": "u64"},
}


def get_openapi_spec(path: str):
    """Load OpenAPI spec from a file"""
    with open(path, "r") as fp:
        spec_data = jsonref.replace_refs(yaml.safe_load(fp))
    return Spec.from_dict(spec_data)


def find_openapi_operation(spec, operationId: str):
    """Find operation by operationId in the loaded spec"""
    for path, path_spec in spec["paths"].items():
        for method, method_spec in path_spec.items():
            if not isinstance(method_spec, dict):
                continue
            if method_spec.get("operationId") == operationId:
                return (path, method, method_spec)
    raise RuntimeError("Cannot find operation %s specification" % operationId)


def get_plural_form(resource):
    """Get plural for of the resource"""
    if resource[-1] == "y":
        return resource[0:-1] + "ies"
    if resource[-1] == "s":
        return resource[0:-1] + "es"
    else:
        return resource + "s"


def get_normalized_field_type(schema):
    """Get a single supported type for the field/attribute

    Field can be a fixed type, type can be list of few possibilties (i.e. string, integer) or it can be a oneOf
    This method tries to get a single type ouf of those possibilities.
    """
    xtype = None
    if "type" in schema:
        xtype = schema["type"]
    elif "oneOf" in schema:
        # field itself is oneOf
        # {'oneOf': [{'type': 'string', 'format': 'uuid'}, {'type': 'string', 'maxLength': 0}]}
        oneOf = schema["oneOf"]
        # Build a set of uniqie candidate types to figure out whether they
        # are all same
        types = set([x["type"] for x in oneOf])
        if len(types) == 1:
            # Current known case is that both are strings and only differ in
            # format. Ignore that difference.
            # Server side should take care of validation of the format, the
            # client is only interested in which type is the field.
            xtype = types.pop()
        elif len(types) == 2 and "null" in types:
            # {'oneOf': [{'type': 'string', 'format': 'uuid'}, {'type': 'null'}]}
            # Here we can just replace oneOf with [string, null]
            xtype = list(types)
        else:
            # TODO(gtema) generally here we could build an enum
            raise RuntimeError(
                "Cannot agree on the single type for %s" % (schema)
            )
    else:
        raise RuntimeError("Cannot agree on the single type for %s" % (schema))
    return xtype


def find_resource_schema(schema: dict, parent: str = None, resource_name=None):
    """Find the actual resource schema in the body schema

    Traverse through the body schema searching for an element that represent
    the resource itself.

    a) root is an object and it contain property with the resource name
    b) root is an object and it contain array property with name equals to
       the plural form of the resource name

    :returns: tuple of (schema, attribute name) for the match or (None, None)
        if not found

    """
    if "type" not in schema:
        # Response of server create is a server or reservation_id
        raise RuntimeError("No type in %s" % schema)
    schema_type = schema["type"]
    if schema_type == "array":
        if parent and parent == get_plural_form(resource_name):
            return (schema, parent)
        return find_resource_schema(
            schema["items"], parent, resource_name=resource_name
        )
    elif schema_type == "object":
        props = (
            schema.properties
            if hasattr(schema, "properties")
            else schema.get("properties", {})
        )
        if not parent and resource_name in props:
            # we are at the top level and there is property with the resource
            # name - it is what we are searching for
            return (props[resource_name], resource_name)
        for name, item in props.items():
            (r, path) = find_resource_schema(item, name, resource_name)
            if r:
                return (r, path)
    return (None, None)


def get_resource_names_from_url(path: str):
    """Construct Resource name from the URL"""
    path_elements = list(filter(None, path.split("/")))
    if path_elements and VERSION_RE.match(path_elements[0]):
        path_elements.pop(0)
    path_resource_names = []

    # if len([x for x in all_paths if x.startswith(path + "/")]) > 0:
    #     has_subs = True
    # else:
    #     has_subs = False
    for path_element in path_elements:
        if "{" not in path_element:
            el = path_element.replace("-", "_")
            if el[-3:] == "ies":
                path_resource_names.append(el[0:-3] + "y")
            elif el[-1] == "s" and el[-3:] != "dns" and el[-6:] != "access":
                path_resource_names.append(el[0:-1])
            else:
                path_resource_names.append(el)
    if len(path_resource_names) > 1 and path_resource_names[-1] in [
        "action",
        "detail",
    ]:
        path_resource_names.pop()
    if len(path_resource_names) == 0:
        return ["Version"]
    # print(f"{path} => {path_resource_names}")
    return path_resource_names


def get_rust_type(param: dict, required: bool = False, mapping=None):
    """Convert json type into suitable Rust type"""
    if "schema" in param:
        schema = param["schema"]
    else:
        schema = param
    param_type = get_normalized_field_type(schema)
    # if "type" in schema:
    #     param_type: str = schema["type"]
    # else:
    #     print(schema)
    #     raise RuntimeError("No type for %s" % param)
    if isinstance(param_type, list):
        if "null" in param_type:
            required = False
            param_type.remove("null")
        if len(param_type) == 1:
            param_type = param_type[0]
        elif param_type.sort() == ["integer", "string"].sort():
            param_type = "intstring"
        else:
            raise RuntimeError("property type list is not supported yet")
    res: str = None
    if not mapping:
        mapping = OPENAPI_RUST_TYPE_MAPPING
    if param_type == "array":
        res = "Vec<" + mapping[schema["items"]["type"]]["default"] + ">"
    else:
        if isinstance(param_type, list):
            if len(param_type) == 2 and "null" in param_type:
                # One of types is null - do nothing and let the Option be set by required
                param_type = [x for x in param_type if x != "null"][0]
            else:
                raise ValueError("Cannot serialize %s type" % param_type)
        else:
            if param_type == "null":
                return "Option<String>"
            typ = mapping.get(param_type)
            if typ:
                if "format" in schema and schema["format"] in typ:
                    res = typ[schema["format"]]
                else:
                    res = typ["default"] if "default" in typ else typ
            else:
                raise RuntimeError("No mapping for type `%s`" % param_type)
    if not required:
        res = f"Option<{res}>"
    return res


def get_rust_param_dict(param: dict, dest: str = "sdk"):
    """Prepare param for rust"""
    param_location = param.get("in", "query")
    param_name = param["name"]
    param_schema = param["schema"]
    param_builder_args = ["default"]
    param_clap_args = []
    additional_imports = set()
    param_required = param.get("required", False)
    local_name = param.get(
        "x-openstack-sdk-name",
        param_schema.get(
            "x-openstack-sdk-name",
            param_name.replace("-", "_").replace(":", "_"),
        ),
    )
    if param_location != "path":
        param_clap_args.append("long")
    elif param_name == "project_id" and dest == "cli":
        # Project id is a special path param that if not set uses token project_id
        param_clap_args.append("long")
        param_required = False
        additional_imports.add("openstack_sdk::api::RestClient")

    param_setter = None
    rust_type = get_rust_type(
        param,
        param_required,
        mapping=OPENAPI_RUST_TYPE_MAPPING
        if dest == "sdk"
        else OPENAPI_RUST_CLI_TYPE_MAPPING,
    )
    #    if isinstance(param_schema["type"], list):
    #        raise RuntimeError("API Parameter type list is not supported: %s" % param_schema)

    if param_schema["type"] == "string":
        if dest == "sdk":
            param_builder_args.append("setter(into)")
    elif param_schema["type"] == "array":
        if dest == "sdk":
            param_builder_args.append("private")
            param_builder_args.append(f'setter(name="_{local_name}")')
            param_style = param.get("style", "form")
            param_explode = param.get("explode", False)
            if param_schema["items"].get("type") == "string":
                if param_style:
                    if not param_explode:
                        rust_type = "CommaSeparatedList<Cow<'a, str>>"
                        setter_type = "csv"
                    else:
                        rust_type = "BTreeSet<Cow<'a, str>>"
                        setter_type = "set"
                        additional_imports.add("std::collections::BTreeSet")
                else:
                    raise ValueError(
                        "array with style=%s is not supported yet"
                        % param_style
                    )
            param_setter = dict(
                name=local_name,
                type=setter_type,
                element="Cow<'a, str>",
                is_optional=False,
                description=param.get("description"),
            )
            if not param_required and not rust_type.startswith("BTreeSet"):
                rust_type = f"Option<{rust_type}>"
        elif dest == "cli":
            param_clap_args.append("action=clap::ArgAction::Append")
    elif param_schema["type"] == "boolean":
        param_clap_args.append("action=clap::ArgAction::Set")

    struct_param_macros = []
    if dest == "cli":
        struct_param_macros.append(f"#[arg({', '.join(param_clap_args)})]")
    if dest == "sdk" and param_builder_args:
        struct_param_macros.append(
            f"#[builder({', '.join(param_builder_args)})]"
        )
    return (
        dict(
            name=param_name,
            local_name=local_name,
            location=param_location,
            type=rust_type,
            schema=param_schema,
            description=param.get("description"),
            required=param_required,
            param_macros=struct_param_macros,
            additional_imports=additional_imports,
        ),
        param_setter,
    )


def get_rust_sdk_subtype_name(name: str):
    """Construct name for the subobject"""
    return "".join([x.capitalize() for x in name.split("_")])


def get_rust_sdk_sub_object_dict(name: str, obj: dict, description: str):
    """Build a subtype object representation data

    Since subtypes require dedicated struct to be created with no builder
    pattern this function is doing work a little bit differently.

    :param str name: parent object name (local_name)
    :param dict obj: openapi spec of the object
    :param str description: Subtype description
    """
    subtypes = {}
    additional_imports = set()
    new_subclass_name = get_rust_sdk_subtype_name(name)
    subtypes[new_subclass_name] = {
        "description": description
        or obj.get("description", new_subclass_name),
        "params": {},
    }
    lifetime = ""
    for k, v in obj.get("properties", {}).items():
        required = k in obj.get("required", [])
        if not v:
            # Nova create_server legacy_block_device_mapping contain
            # no_device empty field. This is not really correct, just skip it
            continue
        (sub_param, _, subsubtypes) = get_rust_body_element_dict(
            k, v, required, "sdk"
        )
        sub_param["builder_args"] = []
        sub_param["param_macros"] = []
        if not required and "Option" in sub_param["type"]:
            sub_param["param_macros"].append(
                '#[serde(skip_serializing_if = "Option::is_none")]'
            )

        if "'a" in sub_param["type"]:
            lifetime = "<'a>"
        subtypes[new_subclass_name]["params"][sub_param["name"]] = sub_param
        additional_imports.update(sub_param["additional_imports"])
        subtypes.update(subsubtypes)
    rust_type = f"{new_subclass_name}{lifetime}"
    return (rust_type, subtypes, additional_imports)


def get_rust_sdk_enum_dict(name: str, choices: list[dict]):
    """Build a subtype enum representation data

    :param str name: parent object name (local_name)
    :param dict obj: openapi spec of the object
    """
    raise NotImplementedError


# class EnumField:
#    local_name: str = None
#    remote_name: str = None
#    kinds: dict[str, BaseType] = {}
#    additional_imports: set = set()


def _optional_wrap(local_type, is_optional):
    return f"Optional<{local_type}>" if is_optional else local_type


# class RustDataType(types.BaseType):
#    type_hint: str
#
#    def __init__(self, type_):
#        super().__init__(type_)
#
#        if type_.type:
#            type__ = getattr(types.Types, type_.type)
#            mapped_type = model_type_mapping.get(type__)
#            self.type_hint = mapped_type
#        if not self.type_hint:
#            self.type_hint = "foobar"


# model_type_mapping: dict[types, str] = {
#    Types.integer: "i32",
#    Types.int32: "i32",
#    Types.number: "f32",
#    Types.float: "f32",
#    Types.double: "f64",
#    Types.decimal: "i32",
#    Types.string: "Cow<'a, str>",
#    Types.uuid: "Cow<'a, str>",
#    Types.boolean: "bool",
# }


# class RustSdkProcessor:
#    body_model: types.BaseType = None
#
#    model_type_mapping: dict[types, str] = {
#        Types.integer: "i32",
#        Types.int32: "i32",
#        Types.number: "f32",
#        Types.float: "f32",
#        Types.double: "f64",
#        Types.decimal: "i32",
#        Types.string: "Cow<'a, str>",
#        Types.uuid: "Cow<'a, str>",
#        Types.boolean: "bool",
#    }
#
#    class FieldWrapper:
#        field: Field
#        dest_type_name: str
#
#        def __init__(self, field):
#            self.field = field
#            dt = field.data_type
#            if dt.is_custom_type:
#                self.dest_type_name = field.name
#            else:
#                if dt.type:
#                    self.dest_type_name = RustSdkProcessor.model_type_mapping[
#                        field.type
#                    ]
#
#        def __getattr__(self, name):
#            return getattr(self.field, name)
#
#        def get_macros(self):
#            return []
#
#        def get_local_name(self):
#            return self.field.name
#
#        def get_local_type(self):
#            return self.field.data_type.type
#
#    def get_body_lifetimes(self):
#        return ""
#
#    def get_body_fields(self):
#        print(f"Body model2 is {self.body_model}")
#        if self.body_model:
#            print(
#                f"Type is {self.body_model.data_type.type} {self.body_model.data_type} {Types.object}"
#            )
#        if (
#            self.body_model
#            and self.body_model.data_type.type == Types.object.name
#        ):
#            print("We are in the object")
#            for field in self.body_model.data_type.children:
#                print(f"Emiting {field}")
#                yield (field.name, self.FieldWrapper(field))
#        else:
#            return []
#
#    def set_body_model(self, model: types.Field):
#        self.body_model = model
#        # loc = self._get_data_type(field.data_type)
#
#    def _get_data_type(self, dt: types.DataType):
#        cls = RustDataType(dt)
#        return cls


class RustBodyField:
    """Holder for the data required to represent type in the body"""

    local_name: str = None
    param_name: str = None
    additional_imports: set
    param_builder_args: list
    param_clap_args: list
    param_serde_args: list
    struct_param_macros: list
    param_structable_args: list
    subtypes: dict
    subtype: str
    xtype = None
    param_setter = None
    required: bool = False

    def __init__(self):
        self.additional_imports = set()
        self.param_builder_args = list()
        self.param_clap_args = list()
        self.param_serde_args = list()
        self.struct_param_macros = list()
        self.param_structable_args = list()
        self.subtypes = dict()
        self.subtype = None

    def process_object_sdk(self, data):
        prop_types = set()
        for prop in data.get("properties", {}).values():
            prop_type = prop.get("type")
            if isinstance(prop_type, list):
                if "null" in prop_type:
                    prop_type.remove("null")
                if len(prop_type) == 1:
                    prop_type = prop_type[0]
                if isinstance(prop_type, list) and "string" in prop_type:
                    # When we have intORstring boolORstring, etc we can restrict ourselves to a non-string (api accepts string, okay, but we want to send int)
                    prop_type.remove("string")
                if len(prop_type) == 1:
                    prop_type = prop_type[0]
                else:
                    raise RuntimeError(
                        "Cannot decide on the field type %s:%s"
                        % (prop.get("type"))
                    )
            prop_types.add(prop_type)
        print(f"{self}")
        if len(prop_types) > 1:
            (self.xtype, xsubtypes, ximports) = get_rust_sdk_sub_object_dict(
                self.local_name, data, data.get("description")
            )
            self.subtypes.update(xsubtypes)
            self.additional_imports.update(ximports)
            self.param_builder_args.append("setter(into)")
            self.additional_imports.add("serde::Serialize")
            self.additional_imports.add("serde::Deserialize")
        else:
            pattern_props = data.get("patternProperties", {})
            if pattern_props:
                patterns = list(pattern_props.keys())
                if (
                    len(patterns) == 1
                    and pattern_props[patterns[0]].get("type") == "string"
                ):
                    self.xtype = "BTreeMap<Cow<'a, str>, Cow<'a, str>>"
                    self.additional_imports.add("std::collections::BTreeMap")
                    self.param_builder_args.append("private")
                    self.param_builder_args.append(
                        f'setter(name="_{self.local_name}")'
                    )

                    self.param_setter = dict(
                        name=self.local_name,
                        type="kv",
                        key_type="Cow<'a, str>",
                        value_type="Cow<'a, str>",
                        is_optional=not self.required,
                        description=data.get("description"),
                    )

            if not self.xtype:
                self.xtype = "Value"
                self.additional_imports.add("serde_json::Value")
        if not self.required:
            self.xtype = f"Option<{self.xtype}>"

    def process_object_cli_response(self, data):
        prop_types = set()
        for prop in data.get("properties", {}).values():
            prop_types.add(prop.get("type"))
        if len(prop_types) > 1:
            self.additional_imports.add("crate::common::parse_json")
            self.additional_imports.add("serde_json::Value")
            self.xtype = "Value"
            self.subtype = get_rust_sdk_subtype_name(self.local_name)
        else:
            pattern_props = data.get("patternProperties", {})
            if pattern_props:
                patterns = list(pattern_props.keys())
                if (
                    len(patterns) == 1
                    and pattern_props[patterns[0]].get("type") == "string"
                ):
                    self.additional_imports.add(
                        "crate::common::HashMapStringString"
                    )
                    self.xtype = "HashMapStringString"

            if not self.xtype:
                self.additional_imports.add("serde_json::Value")
                self.xtype = "Value"
        if not self.required:
            self.xtype = f"Option<{self.xtype}>"

    def process_object_cli_input(self, data):
        prop_types = set()
        for prop in data.get("properties", {}).values():
            prop_types.add(prop.get("type"))
        if len(prop_types) > 1:
            self.param_clap_args.append("value_parser=parse_json")
            self.param_clap_args.append('value_name="JSON_VALUE"')
            self.additional_imports.add("crate::common::parse_json")
            self.additional_imports.add("serde_json::Value")
            self.xtype = "Value"
            self.subtype = get_rust_sdk_subtype_name(self.local_name)
        else:
            pattern_props = data.get("patternProperties", {})
            if pattern_props:
                patterns = list(pattern_props.keys())
                if (
                    len(patterns) == 1
                    and pattern_props[patterns[0]].get("type") == "string"
                ):
                    self.additional_imports.add("std::collections::HashMap")
                    self.param_clap_args.extend(
                        [
                            'value_name="key=value"',
                            "value_parser=parse_key_val::<String, String>",
                        ]
                    )
                    self.xtype = "Vec<(String, String)>"
                    self.additional_imports.add("crate::common::parse_key_val")

            if not self.xtype:
                self.param_clap_args.append("value_parser=parse_json")
                self.param_clap_args.append('value_name="JSON_VALUE"')
                self.additional_imports.add("crate::common::parse_json")
                self.additional_imports.add("serde_json::Value")
                self.xtype = "Value"
        if not self.required:
            self.xtype = f"Option<{self.xtype}>"

    def process_list_of_objects_sdk(self, data, description):
        if "properties" in data:
            (xtype, xsubtypes, ximports) = get_rust_sdk_sub_object_dict(
                self.local_name, data, data.get("description")
            )
            self.xtype = f"Vec<{xtype}>"
            self.subtypes.update(xsubtypes)
            self.additional_imports.update(ximports)
            self.param_builder_args.append("setter(into)")
            self.additional_imports.add("serde::Serialize")
            self.additional_imports.add("serde::Deserialize")

        else:
            self.xtype = "Vec<Value>"
            # param_builder_args.append("setter(into)")
            self.additional_imports.add("serde_json::Value")
            self.param_builder_args.append(
                f'setter(name="_{self.local_name}")'
            )
            self.param_builder_args.append("private")
            self.param_setter = dict(
                name=self.local_name,
                type="list",
                element="Value",
                is_optional=not self.required,
                description=description,
            )
        if not self.required:
            self.xtype = f"Option<{self.xtype}>"

    def get_rust_cli_list_object_param_dict(self, data):
        self.xtype = "Vec<Value>"
        self.param_clap_args.append("action=clap::ArgAction::Append")
        self.param_clap_args.append("value_parser=parse_json")
        self.param_clap_args.append('value_name="JSON_VALUE"')
        self.additional_imports.add("crate::common::parse_json")
        self.additional_imports.add("serde_json::Value")
        self.subtype = get_rust_sdk_subtype_name(self.local_name)
        if not self.required:
            self.xtype = f"Option<{self.xtype}>"


def get_rust_body_element_dict(
    name: str, data: dict, required: bool, dest: str = "sdk"
):
    """Prepare schema body field for rust"""
    param_location = "body"
    param_name = name
    local_name = data.get(
        "x-openstack-sdk-name", param_name.replace("-", "_").replace(":", "_")
    )
    # rust_type = None
    try:
        xtype = get_normalized_field_type(data)
    except Exception:
        # So we are most likely in the complex oneOf. We need to build an enum
        oneOf = data.get("oneOf")
        if oneOf:
            holder = RustBodyField()
            holder.local_name = local_name
            holder.required = required
            holder.param_builder_args.append("default")
            holder.param_clap_args.append("long")
            holder.xtype = local_name.title()
            is_nullable = False
            (type_name, subtypes, additional_imports) = get_rust_sdk_enum_dict(
                name, oneOf
            )
            # todo
            # Counter for giving unique suffixes to the candidates
            cnt = 0
            for candidate in oneOf:
                cnt += 1
                os_ext = candidate.get("x-openstack", {})
                key_name = os_ext.get("key-name", f"{name}F{cnt}")
                (dt, _setters, _subtypes) = get_rust_body_element_dict(
                    key_name, candidate, True, dest
                )
                print(f"Result of a complex crap: {dt} {_setters} {_subtypes}")
                if _subtypes:
                    holder.subtypes.update(_subtypes)
                holder.subtypes[key_name] = dt
                if _setters:
                    holder.param_setter.update(_setters)

            if param_name != holder.local_name:
                holder.param_serde_args.append(f'rename = "{param_name}"')

            return (
                dict(
                    name=param_name,
                    local_name=holder.local_name,
                    location=param_location,
                    type=holder.xtype,
                    schema=data,
                    description=data.get("description"),
                    required=holder.required,
                    builder_args=holder.param_builder_args,
                    param_macros=holder.struct_param_macros,
                    param_structable_args=holder.param_structable_args,
                    param_serde_args=holder.param_serde_args,
                    additional_imports=holder.additional_imports,
                    subtype=holder.subtype,
                ),
                holder.param_setter,
                holder.subtypes,
            )

        raise RuntimeError(
            "Cannot determine type of the %s (%s)" % (param_name, data)
        )
    else:
        # No exception, we can continue the normal way - a relatively straight forward object
        holder = RustBodyField()
        holder.local_name = local_name
        holder.required = required
        holder.param_builder_args.append("default")
        holder.param_clap_args.append("long")
        is_nullable = False
        if holder.local_name == "type":
            holder.local_name = "xtype"
            holder.param_structable_args.append('title="type"')

        if param_name != holder.local_name:
            holder.param_serde_args.append(f'rename = "{param_name}"')

        # Figure out what are we dealing with when property type is a list
        if isinstance(xtype, list):
            if "null" in xtype:
                # holder.required = False
                xtype.remove("null")
                is_nullable = True
            if len(xtype) == 1:
                xtype = xtype[0]

        if xtype == "string":
            holder.param_builder_args.append("setter(into)")
        if xtype == "array":
            items = data["items"]
            items_type = items["type"]
            if items_type == "string":
                if dest == "sdk":
                    # rust_type = "BTreeSet<Cow<'a, str>>"
                    holder.xtype = "BTreeSet<Cow<'a, str>>"
                    holder.param_builder_args.append("private")
                    holder.param_builder_args.append(
                        f'setter(name="_{local_name}")'
                    )
                    # setter_type = "set"
                    holder.param_setter = dict(
                        name=holder.local_name,
                        type="set",
                        element="Cow<'a, str>",
                        is_optional=not holder.required,
                        description=data.get("description"),
                    )
                    holder.additional_imports.add("std::collections::BTreeSet")

                elif dest in ["cli-response", "cli-request", "cli"]:
                    holder.xtype = "Vec<String>"
                    holder.param_clap_args.append(
                        "action=clap::ArgAction::Append"
                    )

                if not holder.required:
                    holder.xtype = f"Option<{holder.xtype}>"

            elif items_type == "object" and dest in [
                "cli-request",
                "cli-response",
                "cli",
            ]:
                holder.get_rust_cli_list_object_param_dict(items)
            elif items_type == "object" and dest == "sdk":
                holder.process_list_of_objects_sdk(
                    items, data.get("description")
                )
            if holder.xtype is None:
                raise ValueError(
                    "Array of %s is not supported yet in %s for %s"
                    % (items_type, dest, param_name)
                )

        elif xtype == "object" and dest in ["cli-request"]:
            holder.process_object_cli_input(data)
        elif xtype == "object" and dest in ["cli-response", "cli"]:
            holder.process_object_cli_response(data)
        elif xtype == "object" and dest == "sdk":
            holder.process_object_sdk(data)

        else:
            mapping = None
            if dest == "sdk":
                mapping = OPENAPI_RUST_TYPE_MAPPING
            elif dest == "cli-request":
                mapping = OPENAPI_RUST_CLI_REQUEST_TYPE_MAPPING
            else:
                mapping = OPENAPI_RUST_CLI_TYPE_MAPPING
            holder.xtype = get_rust_type(
                data,
                required,
                mapping=mapping,
                # OPENAPI_RUST_TYPE_MAPPING
                # if dest == "sdk"
                # else OPENAPI_RUST_CLI_TYPE_MAPPING,
            )
            if "NumString" in holder.xtype:
                holder.additional_imports.add("crate::common::NumString")

        if "Option" in holder.xtype:
            holder.param_structable_args.append("optional")

        if is_nullable:
            holder.xtype = f"Option<{holder.xtype}>"

        #    struct_param_macros = []
        if dest in ["cli-request", "cli-response", "cli"]:
            holder.struct_param_macros.append(
                f"#[arg({', '.join(holder.param_clap_args)})]"
            )
        if dest == "sdk" and holder.param_builder_args:
            holder.struct_param_macros.append(
                f"#[builder({', '.join(holder.param_builder_args)})]"
            )

        return (
            dict(
                name=param_name,
                local_name=holder.local_name,
                location=param_location,
                type=holder.xtype,
                schema=data,
                description=data.get("description"),
                required=holder.required,
                builder_args=holder.param_builder_args,
                param_macros=holder.struct_param_macros,
                param_structable_args=holder.param_structable_args,
                param_serde_args=holder.param_serde_args,
                additional_imports=holder.additional_imports,
                subtype=holder.subtype,
            ),
            holder.param_setter,
            holder.subtypes,
        )


def get_rust_sdk_mod_path(service_type: str, api_version: str, path: str):
    """Construct mod path for rust sdk"""
    mod_path = [
        service_type.replace("-", "_"),
        api_version,
    ]
    mod_path.extend([x.lower() for x in get_resource_names_from_url(path)])
    # [i for i in path.split("/") if i]
    # for i in range(len(path_elements)):
    #    curr = path_elements[i]
    #    if i != len(path_elements) - 1 and path_elements[i + 1][0:1] == "{":
    #        mod_path.append(curr[:-1].replace("-", "_"))
    #    elif curr[0:1] != "{":
    #        mod_path.append(curr.replace("-", "_"))
    return mod_path


# def get_last_path_parameter(path: str):
#    return [el[1:-1] for el in path.split("/") if el[0:1] == "{"][-1]


def get_rust_service_type_from_str(xtype: str):
    match xtype:
        case "block-storage":
            return "BlockStorage"
        case "block_storage":
            return "BlockStorage"
        case "compute":
            return "Compute"
        case "image":
            return "Image"
        case "network":
            return "Network"
        case "object-store":
            return "ObjectStore"
        case _:
            return xtype
