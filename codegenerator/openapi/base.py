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
import abc
import copy
import datetime
import importlib
import inspect
import logging
from pathlib import Path
from typing import Any
import re

from codegenerator.common.schema import ParameterSchema
from codegenerator.common.schema import PathSchema
from codegenerator.common.schema import SpecSchema
from codegenerator.common.schema import TypeSchema
from openapi_core import Spec
from ruamel.yaml.scalarstring import LiteralScalarString
from ruamel.yaml import YAML
from wsme import types as wtypes


VERSION_RE = re.compile(r"[Vv][0-9.]*")


def get_referred_type_data(func, name: str):
    """Get python type object referred by the function

    Return `some.object` for a function like:

        @wsgi.validation(some.object)
        def foo():
            pass

    :param func: Function
    :param str name: object name
    """
    module = inspect.getmodule(func)
    if module:
        (mod, obj) = (None, None)
        if "." in name:
            (mod, obj) = name.split(".")
        else:
            raise RuntimeError('No "." in %s', name)
        m = importlib.import_module(module.__name__)
        if hasattr(m, mod):
            mod = getattr(m, mod)
        else:
            raise RuntimeError("Cannot find attr %s", name)
        if hasattr(mod, obj):
            return getattr(mod, obj)
        else:
            raise RuntimeError("Cannot find definition for %s", name)
    else:
        raise RuntimeError("Cannot get module the function was defined in")


class OpenStackServerSourceBase:
    # A URL to Operation tag (OpenApi group) mapping. Can be used when first
    # non parameter path element grouping is not enough
    # ("/qos/policies/{policy_id}/packet_rate_limit_rules" should be
    # "qos-packet-rate-limit-rules" instead of "qos")
    URL_TAG_MAP: dict[str, str] = {}

    def _api_ver_major(self, ver):
        return ver.ver_major

    def _api_ver_minor(self, ver):
        return ver.ver_minor

    def _api_ver(self, ver):
        return (ver.ver_major, ver.ver_minor)

    def useFixture(self, fixture):
        try:
            fixture.setUp()
        except Exception as ex:
            logging.exception("Got exception", ex)
        else:
            return fixture

    @abc.abstractmethod
    def generate(self, target_dir, args) -> Path:
        pass

    def load_openapi(self, path):
        """Load existing OpenAPI spec from the file"""
        if not path.exists():
            return
        yaml = YAML(typ="safe")
        yaml.preserve_quotes = True
        with open(path, "r") as fp:
            spec = yaml.load(fp)

        return SpecSchema(**spec)

    def dump_openapi(self, spec, path, validate=False):
        """Dump OpenAPI spec into the file"""
        if validate:
            self.validate_spec(spec)
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        with open(path, "w") as fp:
            yaml.dump(
                spec.model_dump(
                    exclude_none=True, exclude_defaults=True, by_alias=True
                ),
                fp,
            )

    def validate_spec(self, openapi_spec):
        Spec.from_dict(
            openapi_spec.model_dump(
                exclude_none=True, exclude_defaults=True, by_alias=True
            )
        )

    def _sanitize_param_ver_info(self, openapi_spec, min_api_version):
        # Remove min_version of params if it matches to min_api_version
        for k, v in openapi_spec.components.parameters.items():
            os_ext = v.openstack
            if os_ext:
                if os_ext.get("min-ver") == min_api_version:
                    v.openstack.pop("min-ver")
                if "max_ver" in os_ext and os_ext["max-ver"] is None:
                    v.openstack.pop("max-ver")
            if os_ext == {}:
                v.openstack = None

    def _process_route(
        self, route, openapi_spec, ver_prefix=None, framework=None
    ):
        # Placement exposes "action" as controller in route defaults, all others - "controller"
        if not ("controller" in route.defaults or "action" in route.defaults):
            return
        if "action" in route.defaults and "_methods" in route.defaults:
            # placement 405 handler
            return
        # Path can be "/servers/{id}", but can be
        # "/volumes/:volume_id/types/:(id)" - process
        # according to the routes lib logic
        path = ver_prefix if ver_prefix else ""
        operation_spec = None
        for part in route.routelist:
            if isinstance(part, dict):
                path += "{" + part["name"] + "}"
            else:
                path += part

        if path == "":
            # placement has "" path - see weird explanation in the placement source code
            return

        # if "method" not in route.conditions:
        #    raise RuntimeError("Method not set for %s", route)
        method = (
            route.conditions.get("method", "GET")[0]
            if route.conditions
            else "GET"
        )

        controller = route.defaults.get("controller")
        action = route.defaults.get("action")
        logging.info(
            "Path: %s; method: %s; operation: %s", path, method, action
        )

        versioned_methods = {}
        controller_actions = {}
        framework = None
        if hasattr(controller, "controller"):
            # wsgi
            framework = "wsgi"
            contr = controller.controller
            if hasattr(contr, "versioned_methods"):
                versioned_methods = contr.versioned_methods
            if hasattr(contr, "wsgi_actions"):
                controller_actions = contr.wsgi_actions
            if hasattr(controller, "wsgi_actions"):
                # Nova flavors mess with wsgi_action instead of normal operation
                # and actions on the wrong controller
                parent_controller_actions = controller.wsgi_actions
                if parent_controller_actions:
                    controller_actions.update(parent_controller_actions)
        elif hasattr(controller, "_pecan") or framework == "pecan":
            # Pecan base app
            framework = "pecan"
            contr = controller
        elif not controller and action and hasattr(action, "func"):
            # Placement base app
            framework = "placement"
            controller = action
            contr = action
            action = None
        else:
            raise RuntimeError("Unsupported controller %s" % controller)
        # logging.debug("Actions: %s, Versioned methods: %s", actions, versioned_methods)

        # path_spec = openapi_spec.paths.setdefault(path, PathSchema())

        # operation_spec = dict() #= getattr(path_spec, method.lower())  # , {})
        # Get Path elements
        path_elements: list[str] = list(filter(None, path.split("/")))
        if path_elements and VERSION_RE.match(path_elements[0]):
            path_elements.pop(0)
        operation_tags = self._get_tags_for_url(path)

        # Build path parameters (/foo/{foo_id}/bar/{id} => $foo_id, $foo_bar_id)
        # Since for same path we are here multiple times check presence of
        # parameter before adding new params
        path_params: list[ParameterSchema] = []
        path_resource_names: list[str] = [
            x.replace("-", "_")
            for x in filter(lambda x: not x.startswith("{"), path_elements)
        ]
        for path_element in path_elements:
            if "{" in path_element:
                param_name = path_element.strip("{}")
                global_param_name = (
                    "_".join(path_resource_names) + f"_{param_name}"
                )

                param_ref_name = self._get_param_ref(
                    openapi_spec,
                    global_param_name,
                    param_name,
                    param_location="path",
                    path=path,
                )
                # Ensure reference to the param is in the path_params
                if param_ref_name not in [
                    k.ref for k in [p for p in path_params]
                ]:
                    path_params.append(ParameterSchema(ref=param_ref_name))
        # Cleanup path_resource_names
        # if len(path_resource_names) > 0 and VERSION_RE.match(path_resource_names[0]):
        #    # We should not have version prefix in the path_resource_names
        #    path_resource_names.pop(0)
        if len(path_resource_names) == 0:
            path_resource_names.append("root")
        elif path_elements[-1].startswith("{"):
            rn = path_resource_names[-1]
            if rn.endswith("ies"):
                rn = rn.replace("ies", "y")
            if rn.endswith("sses"):
                rn = rn[:-2]
            else:
                rn = rn.rstrip("s")
            path_resource_names[-1] = rn

        # Set operationId
        operation_id = re.sub(
            r"^(/?v[0-9.]*/)",
            "",
            "/".join([x.strip("{}") for x in path_elements])
            + f":{method.lower()}",  # noqa
        )

        if action in versioned_methods:
            # Normal REST operation with version bounds
            (start_version, end_version) = (None, None)

            # if len(versioned_methods[action]) > 1:
            #   for m in versioned_methods[action]:
            #       raise RuntimeError("Multiple versioned methods for action %s:%s: %s", path, action, versioned_methods[action])
            for versioned_method in sorted(
                versioned_methods[action], key=lambda v: v.start_version
            ):
                start_version = versioned_method.start_version
                end_version = versioned_method.end_version
                func = versioned_method.func

                # Get the path/op spec only when we have
                # something to fill in
                path_spec = openapi_spec.paths.setdefault(
                    path, PathSchema(parameters=path_params)
                )
                operation_spec = getattr(path_spec, method.lower())
                if not operation_spec.operationId:
                    operation_spec.operationId = operation_id
                operation_spec.tags.extend(operation_tags)
                operation_spec.tags = list(set(operation_spec.tags))

                self.process_operation(
                    func,
                    openapi_spec,
                    operation_spec,
                    path_resource_names,
                    controller=controller,
                    method=method,
                    operation_name=action,
                    start_version=start_version,
                    end_version=end_version,
                )
        elif action and hasattr(contr, action):
            # Normal REST operation without version bounds
            func = getattr(contr, action)

            # Get the path/op spec only when we have
            # something to fill in
            path_spec = openapi_spec.paths.setdefault(
                path, PathSchema(parameters=path_params)
            )
            operation_spec = getattr(path_spec, method.lower())
            if not operation_spec.operationId:
                operation_spec.operationId = operation_id
            operation_spec.tags.extend(operation_tags)
            operation_spec.tags = list(set(operation_spec.tags))

            self.process_operation(
                func,
                openapi_spec,
                operation_spec,
                path_resource_names,
                controller=controller,
                operation_name=action,
                method=method,
                path=path,
            )
        elif action != "action" and action in controller_actions:
            # Normal REST operation without version bounds and present in
            # wsgi_actions of child or parent controller. Example is
            # compute.flavor.create/update which are exposed as wsgi actions
            # (BUG)
            func = controller_actions[action]

            # Get the path/op spec only when we have
            # something to fill in
            path_spec = openapi_spec.paths.setdefault(
                path, PathSchema(parameters=path_params)
            )
            operation_spec = getattr(path_spec, method.lower())
            if not operation_spec.operationId:
                operation_spec.operationId = operation_id
            operation_spec.tags.extend(operation_tags)
            operation_spec.tags = list(set(operation_spec.tags))

            self.process_operation(
                func,
                openapi_spec,
                operation_spec,
                path_resource_names,
                controller=controller,
                operation_name=action,
                method=method,
                path=path,
            )

        elif (
            controller_actions and action == "action"
        ):  # and action in controller_actions:
            # There are ACTIONS present on the controller
            for action, op_name in controller_actions.items():
                logging.info("Action %s: %s", action, op_name)
                (start_version, end_version) = (None, None)
                if isinstance(op_name, str):
                    # wsgi action value is a string
                    if op_name in versioned_methods:
                        # ACTION with version bounds
                        if len(versioned_methods[op_name]) > 1:
                            raise RuntimeError(
                                "Multiple versioned methods for action %s",
                                action,
                            )
                        for ver_method in versioned_methods[op_name]:
                            start_version = ver_method.start_version
                            end_version = ver_method.end_version
                            func = ver_method.func
                            logging.info("Versioned action %s", func)
                        # operation_id += f"[{op_name}]"
                    elif hasattr(contr, op_name):
                        # ACTION with no version bounds
                        func = getattr(contr, op_name)
                        # operation_id += f"[{op_name}]"
                        logging.info("Unversioned action %s", func)
                    else:
                        logging.error(
                            "Cannot find code for %s:%s:%s [%s]",
                            path,
                            method,
                            action,
                            dir(contr),
                        )
                        continue
                elif callable(op_name):
                    # Action is already a function (compute.flavors)
                    closurevars = inspect.getclosurevars(op_name)
                    # Versioned actions in nova can be themelves as a
                    # version_select wrapped callable (i.e. baremetal.action)
                    key = closurevars.nonlocals.get("key", None)
                    slf = closurevars.nonlocals.get("self", None)

                    if key and key in versioned_methods:
                        # ACTION with version bounds
                        if len(versioned_methods[key]) > 1:
                            raise RuntimeError(
                                "Multiple versioned methods for action %s",
                                action,
                            )
                        for ver_method in versioned_methods[key]:
                            start_version = ver_method.start_version
                            end_version = ver_method.end_version
                            func = ver_method.func
                            logging.info("Versioned action %s", func)
                    elif slf and key:
                        vm = getattr(slf, "versioned_methods", None)
                        if vm and key in vm:
                            # ACTION with version bounds
                            if len(vm[key]) > 1:
                                raise RuntimeError(
                                    "Multiple versioned methods for action %s",
                                    action,
                                )
                            for ver_method in vm[key]:
                                start_version = ver_method.start_version
                                end_version = ver_method.end_version
                                func = ver_method.func
                            logging.info("Versioned action %s", func)
                    else:
                        func = op_name

                # Get the path/op spec only when we have
                # something to fill in
                path_spec = openapi_spec.paths.setdefault(
                    path, PathSchema(parameters=path_params)
                )
                operation_spec = getattr(path_spec, method.lower())
                if not operation_spec.operationId:
                    operation_spec.operationId = operation_id
                operation_spec.tags.extend(operation_tags)
                operation_spec.tags = list(set(operation_spec.tags))

                self.process_operation(
                    func,
                    openapi_spec,
                    operation_spec,
                    path_resource_names,
                    controller=controller,
                    operation_name=action,
                    method=method,
                    start_version=start_version,
                    end_version=end_version,
                    mode="action",
                    path=path,
                )
        elif framework == "pecan":
            if callable(controller):
                func = controller
            # Get the path/op spec only when we have
            # something to fill in
            path_spec = openapi_spec.paths.setdefault(
                path, PathSchema(parameters=path_params)
            )
            operation_spec = getattr(path_spec, method.lower())
            if not operation_spec.operationId:
                operation_spec.operationId = operation_id
            operation_spec.tags.extend(operation_tags)
            operation_spec.tags = list(set(operation_spec.tags))

            self.process_operation(
                func,
                openapi_spec,
                operation_spec,
                path_resource_names,
                controller=controller,
                operation_name=action,
                method=method,
                path=path,
            )

        elif framework == "placement":
            if callable(controller.func):
                func = controller.func
            # Get the path/op spec only when we have
            # something to fill in
            path_spec = openapi_spec.paths.setdefault(
                path, PathSchema(parameters=path_params)
            )
            operation_spec = getattr(path_spec, method.lower())
            if not operation_spec.operationId:
                operation_spec.operationId = operation_id
            if operation_tags:
                operation_spec.tags.extend(operation_tags)
                operation_spec.tags = list(set(operation_spec.tags))

            self.process_operation(
                func,
                openapi_spec,
                operation_spec,
                path_resource_names,
                controller=controller,
                operation_name=func.__name__,
                method=method,
                path=path,
            )

        else:
            logging.warning(controller.__dict__.items())
            logging.warning(contr.__dict__.items())
            logging.warning("No operation found")

        return operation_spec

    def process_operation(
        self,
        func,
        openapi_spec,
        operation_spec,
        path_resource_names,
        *,
        controller=None,
        operation_name=None,
        method=None,
        start_version=None,
        end_version=None,
        mode=None,
        path: str | None = None,
    ):
        logging.info(
            "%s: %s [%s]",
            (mode or "operation").title(),
            operation_name,
            func,
        )
        deser_schema = None
        deser = getattr(controller, "deserializer", None)
        if deser:
            deser_schema = getattr(deser, "schema", None)
        ser = getattr(controller, "serializer", None)
        # deser_schema = getattr(deser, "schema", None)
        ser_schema = getattr(ser, "schema", None)
        if not ser_schema and hasattr(ser, "task_schema"):
            # Image Task serializer is a bit different
            ser_schema = getattr(ser, "task_schema")

        if mode != "action":
            doc = inspect.getdoc(func)
            if doc and not operation_spec.description:
                operation_spec.description = LiteralScalarString(doc)
        if operation_spec.description:
            # Reading spec from yaml file it was converted back to regular
            # string. Therefore need to force it back to Literal block.
            operation_spec.description = LiteralScalarString(
                operation_spec.description
            )

        action_name = None
        query_params_versions = []
        body_schemas = []
        expected_errors = ["404"]
        response_code = None
        # Version bound on an operation are set only when it is not an
        # "action"
        if (
            mode != "action"
            and start_version
            and self._api_ver_major(start_version) != 0
        ):
            if not (
                "min-ver" in operation_spec.openstack
                and tuple(
                    [
                        int(x)
                        for x in operation_spec.openstack["min-ver"].split(".")
                    ]
                )
                < (self._api_ver(start_version))
            ):
                operation_spec.openstack["min-ver"] = (
                    start_version.get_string()
                )

        if mode != "action" and end_version:
            if end_version.ver_major == 0:
                operation_spec.openstack.pop("max-ver", None)
                operation_spec.deprecated = None
            else:
                # There is some end_version. Set the deprecated flag and wait
                # for final version to be processed which drop it if max_ver
                # is not set
                operation_spec.deprecated = True
                if not (
                    "max-ver" in operation_spec.openstack
                    and tuple(
                        [
                            int(x)
                            for x in operation_spec.openstack["max-ver"].split(
                                "."
                            )
                        ]
                    )
                    > self._api_ver(end_version)
                ):
                    operation_spec.openstack["max-ver"] = (
                        end_version.get_string()
                    )

        action_name = getattr(func, "wsgi_action", None)
        if action_name:
            operation_name = action_name

        # Unwrap operation decorators to access all properties
        f = func
        while hasattr(f, "__wrapped__"):
            closure = inspect.getclosurevars(f)
            closure_locals = closure.nonlocals
            min_ver = closure_locals.get("min_version", start_version)
            max_ver = closure_locals.get("max_version", end_version)

            if "errors" in closure_locals:
                expected_errors = closure_locals["errors"]
                if isinstance(expected_errors, list):
                    expected_errors = [
                        str(x)
                        for x in filter(
                            lambda x: isinstance(x, int), expected_errors
                        )
                    ]
                elif isinstance(expected_errors, int):
                    expected_errors = [str(expected_errors)]
            if "request_body_schema" in closure_locals:
                # Body type is known through method decorator
                obj = closure_locals["request_body_schema"]
                if obj.get("type") in ["object", "array"]:
                    # We only allow object and array bodies
                    # To prevent type name collision keep module name part of the name
                    typ_name = (
                        "".join([x.title() for x in path_resource_names])
                        + func.__name__.title()
                        + (f"_{min_ver.replace('.', '')}" if min_ver else "")
                    )
                    comp_schema = openapi_spec.components.schemas.setdefault(
                        typ_name,
                        self._sanitize_schema(
                            copy.deepcopy(obj),
                            start_version=start_version,
                            end_version=end_version,
                        ),
                    )

                    if min_ver:
                        if not comp_schema.openstack:
                            comp_schema.openstack = {}
                        comp_schema.openstack["min-ver"] = min_ver
                    if max_ver:
                        if not comp_schema.openstack:
                            comp_schema.openstack = {}
                        comp_schema.openstack["max-ver"] = max_ver
                    if mode == "action":
                        if not comp_schema.openstack:
                            comp_schema.openstack = {}
                        comp_schema.openstack["action-name"] = action_name

                    ref_name = f"#/components/schemas/{typ_name}"
                    body_schemas.append(ref_name)
            if "query_params_schema" in closure_locals:
                obj = closure_locals["query_params_schema"]
                query_params_versions.append((obj, min_ver, max_ver))

            f = f.__wrapped__

        if hasattr(func, "_wsme_definition"):
            fdef = getattr(func, "_wsme_definition")
            body_spec = getattr(fdef, "body_type", None)
            if body_spec:
                body_schema = _convert_wsme_to_jsonschema(body_spec)
                schema_name = body_spec.__name__
                openapi_spec.components.schemas.setdefault(
                    schema_name, TypeSchema(**body_schema)
                )
                body_schemas.append(f"#/components/schemas/{schema_name}")
            rsp_spec = getattr(fdef, "return_type", None)
            if rsp_spec:
                ser_schema = _convert_wsme_to_jsonschema(rsp_spec)
            response_code = getattr(fdef, "status_code", None)

        if not body_schemas and deser_schema:
            # Glance may have request deserializer attached schema
            schema_name = (
                "".join([x.title() for x in path_resource_names])
                + func.__name__.title()
                + "Request"
            )
            (body_schema, mime_type) = self._get_schema_ref(
                openapi_spec,
                schema_name,
                description=f"Request of the {operation_spec.operationId} operation",
                schema_def=deser_schema,
            )

        if query_params_versions:
            so = sorted(
                query_params_versions,
                key=lambda d: d[1].split(".") if d[1] else (0, 0),
            )
            for data, min_ver, max_ver in so:
                self.process_query_parameters(
                    openapi_spec,
                    operation_spec,
                    path_resource_names,
                    data,
                    min_ver,
                    max_ver,
                )
        # if body_schemas or mode == "action":
        if method in ["PUT", "POST", "PATCH"]:
            self.process_body_parameters(
                openapi_spec,
                operation_spec,
                path_resource_names,
                body_schemas,
                mode,
                operation_name,
            )

        responses_spec = operation_spec.responses
        for error in expected_errors:
            responses_spec.setdefault(str(error), dict(description="Error"))

            if mode != "action" and str(error) == "410":
                # This looks like a deprecated operation still hanging out there
                operation_spec.deprecated = True
        if not response_code:
            response_codes = getattr(func, "wsgi_code", None)
            if response_codes and not isinstance(response_codes, list):
                response_codes = [response_codes]
        else:
            response_codes = [response_code]
        if not response_codes:
            # No expected response code known, take "normal" defaults
            response_codes = self._get_response_codes(
                method, operation_spec.operationId
            )
        if response_codes:
            for response_code in response_codes:
                rsp = responses_spec.setdefault(
                    str(response_code), dict(description="Ok")
                )
                if str(response_code) != "204" and method != "DELETE":
                    # Arrange response placeholder
                    schema_name = (
                        "".join([x.title() for x in path_resource_names])
                        + (
                            operation_name.replace("index", "list").title()
                            if not path_resource_names[-1].endswith(
                                operation_name
                            )
                            else ""
                        )
                        + "Response"
                    )
                    (schema_ref, mime_type) = self._get_schema_ref(
                        openapi_spec,
                        schema_name,
                        description=(
                            f"Response of the {operation_spec.operationId} operation"
                            if not action_name
                            else f"Response of the {operation_spec.operationId}:{action_name} action"
                        ),  # noqa
                        schema_def=ser_schema,
                        action_name=action_name,
                    )

                    if schema_ref:
                        curr_schema = (
                            rsp.get("content", {})
                            .get("application/json", {})
                            .get("schema", {})
                        )
                        if mode == "action" and curr_schema:
                            # There is existing response for the action. Need to
                            # merge them
                            if isinstance(curr_schema, dict):
                                curr_oneOf = curr_schema.get("oneOf")
                                curr_ref = curr_schema.get("$ref")
                            else:
                                curr_oneOf = curr_schema.oneOf
                                curr_ref = curr_schema.ref
                            if curr_oneOf:
                                if schema_ref not in [
                                    x["$ref"] for x in curr_oneOf
                                ]:
                                    curr_oneOf.append({"$ref": schema_ref})
                            elif curr_ref and curr_ref != schema_ref:
                                rsp["content"]["application/json"][
                                    "schema"
                                ] = TypeSchema(
                                    oneOf=[
                                        {"$ref": curr_ref},
                                        {"$ref": schema_ref},
                                    ]
                                )
                        else:
                            rsp["content"] = {
                                "application/json": {
                                    "schema": {"$ref": schema_ref}
                                }
                            }

        # Ensure operation tags are existing
        for tag in operation_spec.tags:
            if tag not in [x["name"] for x in openapi_spec.tags]:
                openapi_spec.tags.append({"name": tag})

        self._post_process_operation_hook(
            openapi_spec, operation_spec, path=path
        )

    def _post_process_operation_hook(
        self, openapi_spec, operation_spec, path: str | None = None
    ):
        """Hook to allow service specific generator to modify details"""
        pass

    def process_query_parameters(
        self,
        openapi_spec,
        operation_spec,
        path_resource_names,
        obj,
        min_ver,
        max_ver,
    ):
        """Process query parameters in different versions

        It is expected, that this method is invoked in the raising min_ver order to do proper cleanup of max_ver
        """
        # Yey - we have query_parameters
        if obj["type"] == "object":
            params = obj["properties"]
            for prop, spec in params.items():
                param_name = "_".join(path_resource_names) + f"_{prop}"

                param_attrs: dict[str, TypeSchema | dict] = {}
                if spec["type"] == "array":
                    param_attrs["schema"] = TypeSchema(
                        **copy.deepcopy(spec["items"])
                    )
                else:
                    raise RuntimeError("Error")
                if min_ver:
                    os_ext = param_attrs.setdefault("x-openstack", {})
                    os_ext["min-ver"] = min_ver
                if max_ver:
                    os_ext = param_attrs.setdefault("x-openstack", {})
                    os_ext["max-ver"] = max_ver
                ref_name = self._get_param_ref(
                    openapi_spec,
                    param_name,
                    prop,
                    param_location="query",
                    path=None,
                    **param_attrs,
                )
                if ref_name not in [x.ref for x in operation_spec.parameters]:
                    operation_spec.parameters.append(
                        ParameterSchema(ref=ref_name)
                    )

        else:
            raise RuntimeError(
                "Query parameters %s is not an object as expected" % obj
            )

    def process_body_parameters(
        self,
        openapi_spec,
        operation_spec,
        path_resource_names,
        body_schemas,
        mode,
        action_name,
    ):
        op_body = operation_spec.requestBody.setdefault("content", {})
        mime_type: str = "application/json"
        schema_name = None
        # We should not modify path_resource_names of the caller
        path_resource_names = path_resource_names.copy()
        # Create container schema with version discriminator
        if action_name:
            path_resource_names.append(action_name)

        cont_schema_name = (
            "".join([x.title() for x in path_resource_names]) + "Request"
        )
        cont_schema = None

        if len(body_schemas) == 1:
            # There is only one body known at the moment
            if cont_schema_name in openapi_spec.components.schemas:
                # if we have already oneOf - add there
                cont_schema = openapi_spec.components.schemas[cont_schema_name]
                if cont_schema.oneOf and body_schemas[0] not in [
                    x["$ref"] for x in cont_schema.oneOf
                ]:
                    cont_schema.oneOf.append({"$ref": body_schemas[0]})
                schema_ref = f"#/components/schemas/{cont_schema_name}"
            else:
                # otherwise just use schema as body
                schema_ref = body_schemas[0]
        elif len(body_schemas) > 1:
            # We may end up here multiple times if we have versioned operation. In this case merge to what we have already
            old_schema = op_body.get(mime_type, {}).get("schema", {})
            old_ref = (
                old_schema.ref
                if isinstance(old_schema, TypeSchema)
                else old_schema.get("$ref")
            )
            cont_schema = openapi_spec.components.schemas.setdefault(
                cont_schema_name,
                TypeSchema(
                    oneOf=[], openstack={"discriminator": "microversion"}
                ),
            )
            # Add new refs to the container oneOf if they are not already
            # there
            cont_schema.oneOf.extend(
                [
                    {"$ref": n}
                    for n in body_schemas
                    if n not in [x.get("$ref") for x in cont_schema.oneOf]
                ]
            )
            schema_ref = f"#/components/schemas/{cont_schema_name}"
            if (
                old_ref
                and old_ref != schema_ref
                and old_ref not in [x["$ref"] for x in cont_schema.oneOf]
            ):
                # In a previous iteration we only had one schema and decided
                # not to create container. Now we need to change that by
                # merging with previous data
                cont_schema.oneOf.append({"$ref": old_ref})
        elif len(body_schemas) == 0 and mode == "action":
            # There are actions without a real body description, but we know that action requires dummy body
            cont_schema = openapi_spec.components.schemas.setdefault(
                cont_schema_name,
                TypeSchema(
                    description=f"Empty body for {action_name} action",
                    type="object",
                    properties={action_name: {"type": "null"}},
                    openstack={"action-name": action_name},
                ),
            )
            schema_ref = f"#/components/schemas/{cont_schema_name}"
        elif len(body_schemas) == 0:
            # We know nothing about request
            schema_name = (
                "".join([x.title() for x in path_resource_names])
                + (
                    action_name.replace("index", "list").title()
                    if not path_resource_names[-1].endswith(action_name)
                    else ""
                )
                + "Request"
            )
            (schema_ref, mime_type) = self._get_schema_ref(
                openapi_spec,
                schema_name,
                description=f"Request of the {operation_spec.operationId} operation",
                action_name=action_name,
            )

        if mode == "action":
            js_content = op_body.setdefault(mime_type, {})
            body_schema = js_content.setdefault("schema", {})
            one_of = body_schema.setdefault("oneOf", [])
            if schema_ref not in [x.get("$ref") for x in one_of]:
                one_of.append({"$ref": schema_ref})
            os_ext = body_schema.setdefault("x-openstack", {})
            os_ext["discriminator"] = "action"
            if cont_schema and action_name:
                cont_schema.openstack["action-name"] = action_name
        elif schema_ref:
            js_content = op_body.setdefault(mime_type, {})
            body_schema = js_content.setdefault("schema", {})
            operation_spec.requestBody["content"][mime_type]["schema"] = (
                TypeSchema(ref=schema_ref)
            )

    def _sanitize_schema(
        self, schema, *, start_version=None, end_version=None
    ):
        """Various schemas are broken in various ways"""

        if isinstance(schema, dict):
            # Forcibly convert to TypeSchema
            schema = TypeSchema(**schema)
        properties = getattr(schema, "properties", None)
        if properties:
            # Nova aggregates schemas are broken since they have "type": "object" inside "properties
            if properties.get("type") == "object":
                schema.properties.pop("type")

            if "anyOf" in properties:
                # anyOf must be on the properties level and not under (nova host update)
                anyOf = schema.properties.pop("anyOf")
                schema.anyOf = anyOf

            for k, v in properties.items():
                typ = v.get("type")
                if typ == "object":
                    schema.properties[k] = self._sanitize_schema(v)
                if typ == "array" and "additionalItems" in v:
                    # additionalItems have nothing to do under the type array (create servergroup)
                    schema.properties[k].pop("additionalItems")
                if typ == "array" and isinstance(v["items"], list):
                    # server_group create - type array "items" is a dict and not list
                    schema.properties[k]["items"] = v["items"][0]
        if start_version and self._api_ver_major(start_version) not in [
            "0",
            0,
        ]:
            if not schema.openstack:
                schema.openstack = {}
            schema.openstack["min-ver"] = start_version.get_string()
        if end_version and self._api_ver_major(end_version) not in ["0", 0]:
            if not schema.openstack:
                schema.openstack = {}
            schema.openstack["max-ver"] = end_version.get_string()
        return schema

    def _get_param_ref(
        self,
        openapi_spec,
        ref_name: str,
        param_name: str,
        param_location: str,
        path: str | None = None,
        **param_attrs,
    ):
        if ref_name == "_project_id":
            ref_name = "project_id"
        ref_name = ref_name.replace(":", "_")
        # Pop extensions for easier post processing
        if param_attrs:
            os_ext = param_attrs.pop("x-openstack", None)
        else:
            os_ext = None
        # Ensure global parameter is present
        param = ParameterSchema(
            location=param_location, name=param_name, **param_attrs
        )
        if param_location == "path":
            param.required = True
        if not param.description and path:
            param.description = f"{param_name} parameter for {path} API"
        # We can only assume the param type. For path it is logically a string only
        if not param.type_schema:
            param.type_schema = TypeSchema(type="string")
        if os_ext and ("min-ver" in os_ext or "max-ver" in os_ext):
            # min_ver is present
            old_param = openapi_spec.components.parameters.get(ref_name, None)
            if not old_param:
                # Param was not present, just set what we have
                param.openstack = os_ext
            else:
                # Param is already present. Check whether we need to modify min_ver
                min_ver = os_ext.get("min-ver")
                max_ver = os_ext.get("max-ver")
                param.openstack = dict()
                if not old_param.openstack:
                    old_param.openstack = {}
                old_min_ver = old_param.openstack.get("min-ver")
                old_max_ver = old_param.openstack.get("max-ver")
                if old_min_ver and tuple(old_min_ver.split(".")) < tuple(
                    min_ver.split(".")
                ):
                    # Existing param has lower min_ver. Keep the old value
                    os_ext["min-ver"] = old_min_ver
                if (
                    old_max_ver
                    and max_ver
                    and tuple(old_max_ver.split("."))
                    > tuple(max_ver.split("."))
                ):
                    # Existing param has max_ver higher then what we have now. Keep old value
                    os_ext["max_ver"] = old_max_ver
        if os_ext:
            param.openstack = os_ext

        # Overwrite param
        openapi_spec.components.parameters[ref_name] = param
        return f"#/components/parameters/{ref_name}"

    def _get_schema_ref(
        self,
        openapi_spec,
        name,
        description=None,
        schema_def=None,
        action_name=None,
    ) -> tuple[str, str]:
        if not schema_def:
            logging.warn(
                "No Schema definition for %s[%s] is known", name, action_name
            )
            schema_def = {
                "type": "object",
                "description": LiteralScalarString(description),
            }
        schema = openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(
                **schema_def,
            ),
        )

        if action_name:
            if not schema.openstack:
                schema.openstack = {}
            schema.openstack.setdefault("action-name", action_name)

        return (f"#/components/schemas/{name}", "application/json")

    def _get_tags_for_url(self, url):
        """Return Tag (group) name based on the URL"""
        # Drop version prefix
        url = re.sub(r"^(/v[0-9.]*/)", "/", url)

        for k, v in self.URL_TAG_MAP.items():
            if url.startswith(k):
                return [v]
        if url == "/":
            return ["version"]
        path_elements: list[str] = list(filter(None, url.split("/")))
        for el in path_elements:
            # Use 1st (non project_id) path element as tag
            if not el.startswith("{"):
                return [el]

    @classmethod
    def _get_response_codes(cls, method: str, operationId: str) -> list[str]:
        if method == "DELETE":
            response_code = "204"
        elif method == "POST":
            response_code = "201"
        else:
            response_code = "200"
        return [response_code]


def _convert_wsme_to_jsonschema(body_spec):
    """Convert WSME type description to JsonSchema"""
    res: dict[str, Any] = {}
    if wtypes.iscomplex(body_spec) or isinstance(body_spec, wtypes.wsattr):
        res = {"type": "object", "properties": {}}
        doc = inspect.getdoc(body_spec)
        if doc:
            res.setdefault("description", LiteralScalarString(doc))
        required = set()
        for attr in wtypes.list_attributes(body_spec):
            attr_value = getattr(body_spec, attr.key)
            if isinstance(attr_value, wtypes.wsproperty):
                r = _convert_wsme_to_jsonschema(attr_value)
            else:
                r = _convert_wsme_to_jsonschema(attr_value._get_datatype())
            res["properties"][attr.key] = r
            if attr.mandatory:
                required.add(attr.name)
            # todo: required
        if required:
            res.setdefault("required", list(required))
    elif isinstance(body_spec, wtypes.ArrayType):
        res = {
            "type": "array",
            "items": _convert_wsme_to_jsonschema(body_spec.item_type),
        }
    elif isinstance(body_spec, wtypes.StringType) or body_spec is str:
        res = {"type": "string"}
        min_len = getattr(body_spec, "min_length", None)
        max_len = getattr(body_spec, "max_length", None)
        if min_len:
            res["minLength"] = min_len
        if max_len:
            res["maxLength"] = max_len
    elif isinstance(body_spec, wtypes.IntegerType):
        res = {"type": "integer"}
        minimum = getattr(body_spec, "minimum", None)
        maximum = getattr(body_spec, "maximum", None)
        if minimum:
            res["minimum"] = minimum
        if maximum:
            res["maximum"] = maximum
    elif isinstance(body_spec, wtypes.Enum):
        basetype = body_spec.basetype
        values = body_spec.values
        if basetype is str:
            res = {"type": "string"}
        elif basetype is float:
            res = {"type": "number"}
        elif basetype is int:
            res = {"type": "integer"}
        else:
            raise RuntimeError("Unsupported basetype %s" % basetype)
        res["enum"] = list(values)
    # elif hasattr(body_spec, "__name__") and body_spec.__name__ == "bool":
    elif wtypes.isdict(body_spec):
        res = {
            "type": "object",
            "additionalProperties": {
                "type": _convert_wsme_to_jsonschema(body_spec.value_type)
            },
        }
    elif wtypes.isusertype(body_spec):
        basetype = body_spec.basetype
        name = body_spec.name
        if basetype is str:
            res = {"type": "string", "format": name}
        else:
            raise RuntimeError("Unsupported basetype %s" % basetype)
    elif isinstance(body_spec, wtypes.wsproperty):
        res = _convert_wsme_to_jsonschema(body_spec.datatype)
    elif body_spec is bool:
        # wsattr(bool) lands here as <class 'bool'>
        res = {"type": "boolean"}
    elif body_spec is float:
        res = {"type": "number", "format": "float"}
    elif (
        isinstance(body_spec, wtypes.dt_types)
        or body_spec is datetime.datetime
    ):
        res = {"type": "string", "format": "date-time"}
    else:
        raise RuntimeError("Unsupported object %s" % body_spec)

    return res
