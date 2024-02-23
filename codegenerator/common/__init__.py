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
        spec_data = jsonref.replace_refs(yaml.safe_load(fp), proxies=False)
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
    """Get plural for of the resource

    Apply rules from https://www.fluentu.com/blog/english/plural-nouns/ to
    build a plural form of the word
    """
    if resource[-1] == "y":
        return resource[0:-1] + "ies"
    elif resource[-1] == "o":
        return resource + "es"
    elif resource[-2:] == "is":
        return resource[0:-2] + "es"
    elif resource[-1] in ["s", "x", "z"] or resource[-2:] in ["sh", "ch"]:
        return resource + "es"
    elif resource[-1] == "f":
        return resource[:-1] + "ves"
    elif resource[-2:] == "fe":
        return resource[:-2] + "ves"
    else:
        return resource + "s"


def find_resource_schema(
    schema: dict, parent: str | None = None, resource_name: str | None = None
) -> tuple[dict | None, str | None]:
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
                items = schema["items"]
                if (
                    items.get("type") == "object"
                    and resource_name in items.get("properties", [])
                    and len(items.get("properties", []).keys()) == 1
                ):
                    # Most likely this is Keypair where we have keypairs.keypair.{}
                    return (items["properties"][resource_name], parent)
                else:
                    return (items, parent)
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
                # we are at the top level and there is property with the
                # resource name - it is what we are searching for
                el_type = props[resource_name]["type"]
                if el_type == "array":
                    return (props[resource_name]["items"], resource_name)
                return (props[resource_name], resource_name)
            for name, item in props.items():
                if name == "additionalProperties" and isinstance(item, bool):
                    # Some schemas are broken
                    continue
                (r, path) = find_resource_schema(item, name, resource_name)
                if r:
                    return (r, path)
            if not parent:
                # We are on top level and have not found anything.
                keys = list(props.keys())
                if len(keys) == 1:
                    # there is only one field in the object
                    if props[keys[0]].get("type") == "object":
                        # and it is itself an object
                        return (props[keys[0]], keys[0])
                    else:
                        # only field is not an object
                        return (schema, None)
                else:
                    return (schema, None)
    except Exception as ex:
        logging.exception(
            f"Caught exception {ex} during processing of {schema}"
        )
        raise
    return (None, None)


def find_response_schema(
    responses: dict, response_key: str, action_name: str | None = None
):
    """Locate response schema

    Some operations are having variety of possible responses (depending on
    microversion, action, etc). Try to locate suitable response for the client.

    The function iterates over all defined responses and for 2** appies the
    following logic:

    - if action_name is present AND oneOf is present AND action_name is in one
      of the oneOf schemas -> return this schema

    - if action_name is not present AND oneOf is present AND response_key is in
      one of the OneOf candidates' properties (this is an object) -> return it

    - action_name is not present AND oneOf is not present and (response_key or
      plural of the response_key) in candidate -> return it

    :param dict responses: Dictionary with responses as defined in OpenAPI spec
    :param str response_key: Response key to be searching in responses (when
        aciton_name is not given) :param str action_name: Action name to be
    searching response for
    """
    for code, rspec in responses.items():
        if not code.startswith("2"):
            continue
        content = rspec.get("content", {})
        if "application/json" in content:
            response_spec = content["application/json"]
            schema = response_spec["schema"]
            oneof = schema.get("oneOf")
            discriminator = schema.get("x-openstack", {}).get("discriminator")
            if oneof:
                if not discriminator:
                    # Server create returns server or reservation info. For the
                    # cli it is not very helpful and we look for response
                    # candidate with the resource_name in the response
                    for candidate in oneof:
                        if (
                            action_name
                            and candidate.get("x-openstack", {}).get(
                                "action-name"
                            )
                            == action_name
                        ):
                            if response_key in candidate.get("properties", {}):
                                # If there is a object with resource_name in
                                # the props - this must be what we want to look
                                # at
                                return candidate["properties"][response_key]
                            else:
                                return candidate
                        elif (
                            not action_name
                            and response_key
                            and candidate.get("type") == "object"
                            and response_key in candidate.get("properties", {})
                        ):
                            # Actually for the sake of the CLI it may make
                            # sense to merge all candidates
                            return candidate["properties"][response_key]
                else:
                    raise NotImplementedError
            elif (
                not action_name
                and schema
                and (
                    response_key in schema
                    or (
                        schema.get("type") == "object"
                        and (
                            response_key in schema.get("properties", [])
                            or get_plural_form(response_key)
                            in schema.get("properties", [])
                        )
                    )
                )
            ):
                return schema
    if not action_name:
        # Could not find anything with the given response_key. If there is any
        # 200/204 response - return it
        for code in ["200", "204"]:
            if code in responses:
                schema = (
                    responses[code]
                    .get("content", {})
                    .get("application/json", {})
                    .get("schema")
                )
                if schema and "type" in schema:
                    return schema
    return None


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
                part = el[0:-3] + "y"
            elif el[-4:] == "sses":
                part = el[0:-2]
            elif (
                el[-1] == "s"
                and el[-3:] != "dns"
                and el[-6:] != "access"
                and el != "qos"
                # quota/details
                and el != "details"
            ):
                part = el[0:-1]
            else:
                part = el
            if part.startswith("os_"):
                # We should remove `os_` prefix from resource name
                part = part[3:]
            path_resource_names.append(part)
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
        return ["version"]
    if path.startswith("/v2/schemas/"):
        # Image schemas should not be singularized (schema/images,
        # schema/image)
        path_resource_names[-1] = path_elements[-1]
    if path.startswith("/v2/images") and path.endswith("/actions/deactivate"):
        path_resource_names = ["image"]
    if path.startswith("/v2/images") and path.endswith("/actions/reactivate"):
        path_resource_names = ["image"]
    if path_resource_names == ["volume_transfer", "accept"]:
        path_resource_names = ["volume_transfer"]

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
        case "identity":
            return "Identity"
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
