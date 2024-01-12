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
from typing import Any
import re

import jsonref
import yaml
from openapi_core import Spec
from pydantic import BaseModel

VERSION_RE = re.compile(r"[Vv][0-9.]*")
# RE to split name from camelCase or by [`:`,`_`,`-`]
SPLIT_NAME_RE = re.compile(r"(?<=[a-z])(?=[A-Z])|:|_|-")

# FullyQualifiedAttributeName alias map
FQAN_ALIAS_MAP = {"network.floatingip.floating_ip_address": "name"}


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


class BasePrimitiveType(BaseModel):
    lifetimes: set[str] | None = None
    imports: set[str] = set()
    builder_macros: set[str] = set([])


class BaseCombinedType(BaseModel):
    """A Container Type (Array, Option)"""

    pass


class BaseCompoundType(BaseModel):
    """A Complex Type (Enum/Struct)"""

    name: str
    base_type: str
    description: str | None = None


def get_openapi_spec(path: str | Path):
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


def get_plural_form(resource: str) -> str:
    """Get plural for of the resource"""
    if resource[-1] == "y":
        return resource[0:-1] + "ies"
    if resource[-1] == "s":
        return resource[0:-1] + "es"
    else:
        return resource + "s"


def find_resource_schema(
    schema: dict, parent: str | None = None, resource_name: str | None = None
):
    """Find the actual resource schema in the body schema

    Traverse through the body schema searching for an element that represent
    the resource itself.

    a) root is an object and it contain property with the resource name
    b) root is an object and it contain array property with name equals to
       the plural form of the resource name

    :returns: tuple of (schema, attribute name) for the match or (None, None)
        if not found

    """
    try:
        if "type" not in schema:
            # Response of server create is a server or reservation_id
            if "allOf" in schema:
                kinds = {}
                for kind in schema["allOf"]:
                    kinds.update(kind)
                schema["type"] = kinds["type"]
            elif schema == {}:
                return (None, None)
            elif "properties" in schema:
                schema["type"] = "object"
            else:
                raise RuntimeError("No type in %s" % schema)
        schema_type = schema["type"]
        if schema_type == "array":
            if (
                parent
                and resource_name
                and parent == get_plural_form(resource_name)
            ):
                return (schema["items"], parent)
            elif (
                not parent and schema.get("items", {}).get("type") == "object"
            ):
                # Array on the top level. Most likely we are searching for items
                # directly
                return (schema["items"], None)
            return find_resource_schema(
                schema.get("items", {"type": "string"}),
                parent,
                resource_name=resource_name,
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
            if not parent:
                # We are on top level and have not found anything.
                keys = list(props.keys())
                if len(keys) == 1:
                    # there is only one field in the object
                    return (props[keys[0]], keys[0])
                else:
                    return (schema, None)
    except Exception as ex:
        logging.exception(
            f"Caught exception {ex} during processing of {schema}"
        )
        raise
    return (None, None)


def get_resource_names_from_url(path: str):
    """Construct Resource name from the URL"""
    path_elements = list(filter(None, path.split("/")))
    if path_elements and VERSION_RE.match(path_elements[0]):
        path_elements.pop(0)
    path_resource_names = []

    for path_element in path_elements:
        if "{" not in path_element:
            el = path_element.replace("-", "_")
            if el[-3:] == "ies":
                path_resource_names.append(el[0:-3] + "y")
            elif el[-4:] == "sses":
                path_resource_names.append(el[0:-2])
            elif (
                el[-1] == "s"
                and el[-3:] != "dns"
                and el[-6:] != "access"
                and el != "qos"
                # quota/details
                and el != "details"
            ):
                path_resource_names.append(el[0:-1])
            else:
                path_resource_names.append(el)
    if len(path_resource_names) > 1 and (
        path_resource_names[-1]
        in [
            "action",
            "detail",
        ]
        or "add" in path_resource_names[-1]
        or "remove" in path_resource_names[-1]
        or "update" in path_resource_names[-1]
    ):
        path_resource_names.pop()
    if len(path_resource_names) == 0:
        return ["Version"]
    if path.startswith("/v2/schemas/"):
        # Image schemas should not be singularized (schema/images,
        # schema/image)
        if path.endswith("s") and not path_resource_names[-1].endswith("s"):
            path_resource_names[-1] += "s"
    if path.startswith("/v2/images") and path.endswith("/actions/deactivate"):
        path_resource_names = ["image"]
    if path.startswith("/v2/images") and path.endswith("/actions/reactivate"):
        path_resource_names = ["image"]

    return path_resource_names


def get_rust_sdk_mod_path(service_type: str, api_version: str, path: str):
    """Construct mod path for rust sdk"""
    mod_path = [
        service_type.replace("-", "_"),
        api_version,
    ]
    mod_path.extend([x.lower() for x in get_resource_names_from_url(path)])
    return mod_path


def get_rust_cli_mod_path(service_type: str, api_version: str, path: str):
    """Construct mod path for rust sdk"""
    mod_path = [
        service_type.replace("-", "_"),
        api_version,
    ]
    mod_path.extend([x.lower() for x in get_resource_names_from_url(path)])
    return mod_path


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


def make_ascii_string(description: str | None) -> str | None:
    """Make sure a string is a valid ASCII charset

    Placing a text with Unicode chars into the generated code may cause a lot
    of code sanity checks violations. Replace all known Unicode chars with
    something reasonable and return a pure ASCII string
    """
    if not description:
        return None
    # PlusMinus - https://unicodeplus.com/U+00B1
    description = description.replace("\u00b1", "+-")

    return description
