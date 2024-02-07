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
import inspect
from multiprocessing import Process
import logging
from pathlib import Path

from ruamel.yaml.scalarstring import LiteralScalarString

from keystone.assignment import schema as assignment_schema
from keystone.identity import schema as identity_schema
from keystone.resource import schema as ks_schema

from codegenerator.common.schema import ParameterSchema
from codegenerator.common.schema import PathSchema
from codegenerator.common.schema import SpecSchema
from codegenerator.common.schema import TypeSchema
from codegenerator.openapi import keystone_schemas
from codegenerator.openapi.base import OpenStackServerSourceBase
from codegenerator.openapi.utils import merge_api_ref_doc


class KeystoneGenerator(OpenStackServerSourceBase):
    URL_TAG_MAP = {
        "/versions": "version",
    }

    def __init__(self):
        self.api_version = "3.0"
        self.min_api_version = "3.14"

    def _api_ver_major(self, ver):
        return ver._ver_major

    def _api_ver_minor(self, ver):
        return ver._ver_minor

    def _api_ver(self, ver):
        return (ver._ver_major, ver._ver_minor)

    def generate(self, target_dir, args):
        proc = Process(target=self._generate, args=[target_dir, args])
        proc.start()
        proc.join()
        if proc.exitcode != 0:
            raise RuntimeError("Error generating Keystone OpenAPI schema")
        return Path(target_dir, "openapi_specs", "identity", "v3.yaml")

    def _generate(self, target_dir, args, *pargs, **kwargs):
        from keystone.server.flask import application

        self.app = application.application_factory()
        self.router = self.app.url_map

        work_dir = Path(target_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        impl_path = Path(work_dir, "openapi_specs", "identity", "v3.yaml")
        impl_path.parent.mkdir(parents=True, exist_ok=True)

        openapi_spec = self.load_openapi(impl_path)
        if not openapi_spec:
            openapi_spec = SpecSchema(
                info=dict(
                    title="OpenStack Identity API",
                    description=LiteralScalarString(
                        "Identity API provided by Keystone service"
                    ),
                    version=self.api_version,
                ),
                openapi="3.1.0",
                security=[{"ApiKeyAuth": []}],
                components=dict(
                    securitySchemes={
                        "ApiKeyAuth": {
                            "type": "apiKey",
                            "in": "header",
                            "name": "X-Auth-Token",
                        }
                    },
                    headers={
                        "X-Auth-Token": {
                            "description": "A valid authentication token",
                            "schema": {"type": "string", "format": "secret"},
                        },
                        "X-Subject-Token": {
                            "description": "A valid authentication token",
                            "schema": {"type": "string", "format": "secret"},
                        },
                        "Openstack-Auth-Receipt": {
                            "description": "The auth receipt. A partially successful authentication response returns the auth receipt ID in this header rather than in the response body.",
                            "schema": {"type": "string"},
                        },
                    },
                    parameters={
                        "X-Auth-Token": {
                            "in": "header",
                            "name": "X-Auth-Token",
                            "description": "A valid authentication token",
                            "schema": {"type": "string", "format": "secret"},
                        },
                        "X-Subject-Token": {
                            "in": "header",
                            "name": "X-Subject-Token",
                            "description": "The authentication token. An authentication response returns the token ID in this header rather than in the response body.",
                            "schema": {"type": "string", "format": "secret"},
                            "required": True,
                        },
                    },
                ),
            )

        for route in self.router.iter_rules():
            if route.rule.startswith("/static"):
                continue
            # if not route.rule.startswith("/v3/domains"):
            #    continue
            if "/credentials/OS-EC2" in route.rule:
                continue

            self._process_route(route, openapi_spec)

        self._sanitize_param_ver_info(openapi_spec, self.min_api_version)

        if args.api_ref_src:
            merge_api_ref_doc(
                openapi_spec, args.api_ref_src, allow_strip_version=False
            )

        self.dump_openapi(openapi_spec, impl_path, args.validate)

        return impl_path

    def _process_route(self, route, openapi_spec):
        args = route.arguments
        # ep = route.endpoint
        view = self.app.view_functions[route.endpoint]
        controller = None
        if hasattr(view, "view_class"):
            controller = view.view_class

        path = ""
        path_elements = []
        operation_spec = None
        tag_name = None

        for part in route.rule.split("/"):
            if not part:
                continue
            if part.startswith("<"):
                param = part.strip("<>").split(":")
                path_elements.append("{" + param[-1] + "}")
            else:
                if not tag_name and part != "" and part != "v3":
                    tag_name = part
                path_elements.append(part)

        if not tag_name:
            tag_name = "versions"

        path = "/" + "/".join(path_elements)
        if tag_name not in [x["name"] for x in openapi_spec.tags]:
            openapi_spec.tags.append(
                {"name": tag_name, "description": LiteralScalarString("")}
            )
        # Get rid of /v3 for further processing
        path_elements = path_elements[1:]

        # Build path parameters (/foo/{foo_id}/bar/{id} => $foo_id, $foo_bar_id)
        # Since for same path we are here multiple times check presence of
        # parameter before adding new params
        path_params: list[ParameterSchema] = []
        path_resource_names: list[str] = []
        for path_element in path_elements:
            if "{" in path_element:
                param_name = path_element.strip("{}")
                global_param_name = (
                    "_".join(path_resource_names) + f"_{param_name}"
                )
                #                if global_param_name == "_project_id":
                #                    global_param_name = "project_id"
                param_ref_name = f"#/components/parameters/{global_param_name}"
                # Ensure reference to the param is in the path_params
                if param_ref_name not in [
                    k.ref for k in [p for p in path_params]
                ]:
                    path_params.append(ParameterSchema(ref=param_ref_name))
                # Ensure global parameter is present
                path_param = ParameterSchema(
                    location="path", name=param_name, required=True
                )
                # openapi_spec.components.parameters.setdefault(global_param_name, dict())
                if not path_param.description:
                    path_param.description = LiteralScalarString(
                        f"{param_name} parameter for {path} API"
                    )
                # We can only assume the param type. For path it is logically a string only
                path_param.type_schema = TypeSchema(type="string")
                openapi_spec.components.parameters[
                    global_param_name
                ] = path_param
            else:
                path_resource_names.append(path_element.replace("-", "_"))
        if len(path_elements) == 0:
            path_resource_names.append("root")
        elif path_elements[-1].startswith("{"):
            rn = path_resource_names[-1]
            if rn.endswith("ies"):
                rn = rn.replace("ies", "y")
            else:
                rn = rn.rstrip("s")
            path_resource_names[-1] = rn
        if path == "/v3/domains/{domain_id}/config/{group}":
            path_resource_names.append("group")
        elif path == "/v3/domains/config/{group}/{option}/default":
            path_resource_names.append("group")
        elif path == "/v3/domains/{domain_id}/config/{group}/{option}":
            path_resource_names.extend(["group", "option"])

        path_spec = openapi_spec.paths.setdefault(
            path, PathSchema(parameters=path_params)
        )
        # Set operationId
        if path == "/":
            operation_id_prefix = "versions"
        elif path == "/v3":
            operation_id_prefix = "version"
        else:
            operation_id_prefix = "/".join(
                [x.strip("{}") for x in path_elements]
            )
        for method in route.methods:
            if method == "OPTIONS":
                # Not sure what should be done with it
                continue
            if controller:
                func = getattr(
                    controller, method.replace("HEAD", "GET").lower(), None
                )
            else:
                func = view
            # Set operationId
            operation_id = operation_id_prefix + f":{method.lower()}"  # noqa
            # There is a variety of operations that make absolutely no sense and
            # are just not filtered by Keystone itself
            if path == "/v3/users/{user_id}/password" and method in [
                "GET",
                "HEAD",
            ]:
                continue

            # Current Keystone code is having a bug of exposing same controller
            # API for both /RESOURCE and /RESOURCE/{ID}. Routing is then
            # failing to invoke the method because of missing parameter, so
            # analyse and skip those now.
            if not func:
                continue
            sig = inspect.signature(func)
            for param in args:
                if param not in sig.parameters:
                    logging.warn(
                        "Skipping %s:%s because controller does not support parameter %s",
                        path,
                        method,
                        param,
                    )
                    func = None
                    break
            for param in sig.parameters.values():
                if (
                    param.name not in ["self"]
                    and param.default == param.empty
                    and param.name not in args
                ):
                    # Param with no default is not a path argument
                    logging.warn(
                        "Skipping %s:%s because controller requires parameter %s not present in path",
                        path,
                        method,
                        param,
                    )
                    func = None
                    break

            if not func:
                continue

            operation_spec = getattr(path_spec, method.lower())
            if not operation_spec.operationId:
                operation_spec.operationId = operation_id
            doc = inspect.getdoc(func)
            if not operation_spec.description:
                operation_spec.description = LiteralScalarString(
                    doc or f"{method} operation on {path}"
                )
            if tag_name and tag_name not in operation_spec.tags:
                operation_spec.tags.append(tag_name)

            self.process_operation(
                func,
                path,
                openapi_spec,
                operation_spec,
                path_resource_names,
                method=method,
            )

        return operation_spec

    def process_operation(
        self,
        func,
        path,
        openapi_spec,
        operation_spec,
        path_resource_names,
        *,
        method=None,
    ):
        logging.info(
            "Operation: %s [%s]",
            path,
            method,
        )
        if method in ["PUT", "POST", "PATCH"]:
            # This is clearly a modification operation but we know nothing about request
            schema_name = (
                "".join([x.title() for x in path_resource_names])
                + method.title()
                + "Request"
            )

            (schema_ref, mime_type) = self._get_schema_ref(
                openapi_spec,
                schema_name,
                description=f"Request of the {operation_spec.operationId} operation",
            )

            if schema_ref:
                content = operation_spec.requestBody = {"content": {}}
                content["content"][mime_type] = {
                    "schema": {"$ref": schema_ref}
                }

        responses_spec = operation_spec.responses
        # Errors
        for error in ["403", "404"]:
            responses_spec.setdefault(str(error), dict(description="Error"))
        # Response data
        if method == "POST":
            response_code = "201"
        if method == "PUT":
            response_code = "201"
        elif method == "DELETE":
            response_code = "204"
        else:
            response_code = "200"
        if path == "/v3/projects/{project_id}/tags/{value}" and method in [
            "GET",
            "HEAD",
        ]:
            response_code = "204"
        elif path in [
            "/v3/projects/{project_id}/users/{user_id}/roles/{role_id}",
            "/v3/domains/{project_id}/users/{user_id}/roles/{role_id}",
        ] and method in ["GET", "HEAD", "PUT"]:
            response_code = "204"
        elif path in [
            "/v3/projects/{project_id}/groups/{user_id}/roles/{role_id}",
            "/v3/domains/{project_id}/groups/{user_id}/roles/{role_id}",
        ] and method in ["GET", "HEAD", "PUT"]:
            response_code = "204"
        elif path == "/v3/users/{user_id}/password" and method == "POST":
            response_code = "204"
        rsp = responses_spec.setdefault(response_code, dict(description="Ok"))
        if response_code != "204" and method not in ["DELETE", "HEAD"]:
            # Arrange response placeholder
            schema_name = (
                "".join([x.title() for x in path_resource_names])
                + method.title()
                + "Response"
            )
            (schema_ref, mime_type) = self._get_schema_ref(
                openapi_spec,
                schema_name,
                description=f"Response of the {operation_spec.operationId} operation",
            )

            if schema_ref:
                rsp["content"] = {mime_type: {"schema": {"$ref": schema_ref}}}

        if path == "/v3/auth/tokens":
            rsp_headers = rsp.setdefault("headers", {})
            if method == "POST":
                openapi_spec.components.headers["X-Subject-Token"] = {
                    "description": "API Authorization token",
                    "schema": {"type": "string"},
                }
                rsp_headers.setdefault(
                    "X-Subject-Token",
                    {"$ref": "#/components/headers/X-Subject-Token"},
                )
                operation_spec.security = []
            elif method == "GET":
                operation_spec.parameters.append(
                    ParameterSchema(
                        ref="#/components/parameters/X-Subject-Token"
                    )
                )
                rsp_headers.setdefault(
                    "X-Subject-Token",
                    {"$ref": "#/components/headers/X-Subject-Token"},
                )

        self._post_process_operation_hook(openapi_spec, operation_spec)

    def _post_process_operation_hook(self, openapi_spec, operation_spec):
        """Hook to allow service specific generator to modify details"""
        operationId = operation_spec.operationId

        if operationId == "auth/tokens:post":
            (receipt_schema_ref, receipt_mime_type) = self._get_schema_ref(
                openapi_spec, "AuthReceiptSchema"
            )
            operation_spec.responses["401"] = {
                "description": "Unauthorized",
                "headers": {
                    "Openstack-Auth-Receipt": {
                        "$ref": "#/components/headers/Openstack-Auth-Receipt"
                    }
                },
                "content": {
                    receipt_mime_type: {"schema": {"$ref": receipt_schema_ref}}
                },
            }

        elif operationId == "projects:get":
            for key, val in keystone_schemas.PROJECT_LIST_PARAMETERS.items():
                openapi_spec.components.parameters.setdefault(
                    key, ParameterSchema(**val)
                )
                ref = f"#/components/parameters/{key}"
                if ref not in [x.ref for x in operation_spec.parameters]:
                    operation_spec.parameters.append(ParameterSchema(ref=ref))

        elif operationId == "users:get":
            for key, val in keystone_schemas.USER_LIST_PARAMETERS.items():
                openapi_spec.components.parameters.setdefault(
                    key, ParameterSchema(**val)
                )
                ref = f"#/components/parameters/{key}"
                if ref not in [x.ref for x in operation_spec.parameters]:
                    operation_spec.parameters.append(ParameterSchema(ref=ref))

        elif operationId == "users/user_id/application_credentials:get":
            for (
                key,
                val,
            ) in (
                keystone_schemas.APPLICATION_CREDENTIALS_LIST_PARAMETERS.items()
            ):
                openapi_spec.components.parameters.setdefault(
                    key, ParameterSchema(**val)
                )
                ref = f"#/components/parameters/{key}"
                if ref not in [x.ref for x in operation_spec.parameters]:
                    operation_spec.parameters.append(ParameterSchema(ref=ref))

        elif operationId == "OS-FEDERATION/identity_providers:get":
            for (
                key,
                val,
            ) in keystone_schemas.IDENTITY_PROVIDERS_LIST_PARAMETERS.items():
                openapi_spec.components.parameters.setdefault(
                    key, ParameterSchema(**val)
                )
                ref = f"#/components/parameters/{key}"
                if ref not in [x.ref for x in operation_spec.parameters]:
                    operation_spec.parameters.append(ParameterSchema(ref=ref))

        elif operationId in [
            "OS-FEDERATION/projects:get",
            "OS-FEDERATION/projects:head",
            "OS-FEDERATION/domains:get",
            "OS-FEDERATION/domains:head",
        ]:
            operation_spec.deprecated = True

    def _get_schema_ref(
        self,
        openapi_spec,
        name,
        description=None,
        schema_def=None,
        action_name=None,
    ):
        mime_type: str = "application/json"
        # Projects
        if name == "ProjectsPostRequest":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**keystone_schemas.PROJECT_CREATE_REQUEST_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectsPostResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.PROJECT_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectPatchRequest":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**keystone_schemas.PROJECT_UPDATE_REQUEST_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectPatchResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.PROJECT_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectsGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.PROJECTS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.PROJECT_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"

        # Project Tags
        elif name == "ProjectsTagPutRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**ks_schema.project_tag_create)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectsTagsPutRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**ks_schema.project_tags_update)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectsTagsGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.TAGS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectsTagsPutResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.TAGS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"

        # Project/Domain Roles
        elif name == "ProjectsUsersRolesGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.ROLES_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectsGroupsRolesGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.ROLES_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "DomainsUsersRolesGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.ROLES_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "DomainsGroupsRolesGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.ROLES_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"

        # Domains
        elif name == "DomainsPostRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**ks_schema.domain_create)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "DomainsPostResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.DOMAIN_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "DomainPatchRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**ks_schema.domain_update)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "DomainPatchResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.DOMAIN_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "DomainsGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.DOMAINS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "DomainGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.DOMAIN_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"

        # Users
        elif name == "UserPatchRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.USER_PATCH_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "UsersPostRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.USER_CREATE_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "UserPatchResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.USER_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "UsersGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.USERS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "UserGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.USER_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "UsersPasswordPostRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.USER_PWD_CHANGE_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "UsersGroupsGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.USER_GROUPS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "UsersProjectsGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.USER_PROJECTS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"

        # Groups
        elif name == "GroupPatchRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**identity_schema.user_update)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "GroupsPostRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**identity_schema.user_create)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "GroupPatchResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.GROUP_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "GroupsGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.GROUPS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "GroupGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.GROUP_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"

        # Roles
        elif name == "RolesGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.ROLES_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "RolesPostRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**assignment_schema.role_create)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "RolesPostResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.ROLE_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "RoleGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.ROLE_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "RolePatchRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**assignment_schema.role_update)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "RolePatchResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.ROLE_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"

        # Role Implies
        elif name == "RolesImpliesGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.ROLES_INFERENCE_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "RolesImplyGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.ROLE_INFERENCE_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "RolesImplyPutResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.ROLE_INFERENCE_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"

        # Domain Config
        elif name in [
            "DomainsConfigDefaultGetResponse",
            "DomainsConfigPutRequest",
            "DomainsConfigPutResponse",
            "DomainsConfigPatchResponse",
            "DomainsConfigPatchResponse",
            "DomainsConfigDefaultGetResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.DOMAIN_CONFIGS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "DomainsConfigGroupGetResponse",
            "DomainsConfigGroupPatchRequest",
            "DomainsConfigGroupPatchResponse",
            "DomainsConfigGroupPatchResponse",
            "DomainsConfigGroupPatchResponse",
            "DomainsConfigDefaultGroupGetResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.DOMAIN_CONFIG_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"

        # Auth
        elif name == "AuthTokensPostRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.AUTH_TOKEN_ISSUE_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in ["AuthTokensGetResponse", "AuthTokensPostResponse"]:
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.AUTH_SCOPED_TOKEN_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "AuthReceiptSchema":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.AUTH_RECEIPT_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "AuthProjectsGetResponse",
            "Os_FederationProjectsGetResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.AUTH_PROJECTS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "AuthDomainsGetResponse",
            "Os_FederationDomainsGetResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.AUTH_DOMAINS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "AuthSystemGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.AUTH_SYSTEMS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "AuthCatalogGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.AUTH_CATALOG_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "AuthOs_FederationSaml2PostRequest",
            "AuthOs_FederationSaml2EcpPostRequest",
        ]:
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.AUTH_TOKEN_ISSUE_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "AuthOs_FederationSaml2PostResponse",
            "AuthOs_FederationSaml2EcpPostResponse",
        ]:
            mime_type = "text/xml"
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    type="string",
                    format="xml",
                    descripion="SAML assertion in XML format",
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "AuthOs_FederationWebssoGetResponse",
            "AuthOs_FederationWebssoPostResponse",
            "AuthOs_FederationIdentity_ProvidersProtocolsWebssoGetResponse",
            "AuthOs_FederationIdentity_ProvidersProtocolsWebssoPostResponse",
            "Os_FederationIdentity_ProvidersProtocolsAuthGetResponse",
            "Os_FederationIdentity_ProvidersProtocolsAuthPostResponse",
        ]:
            # Federation based auth returns unscoped token even it is not
            # described explicitly in apiref
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**keystone_schemas.AUTH_TOKEN_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "AuthOs_FederationWebssoPostRequest",
            "AuthOs_FederationIdentity_ProvidersProtocolsWebssoPostRequest",
        ]:
            ref = None
        # ### Application Credentials
        elif name == "UsersAccess_RuleGetResponse":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.APPLICATION_CREDENTIAL_ACCESS_RULE_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "UsersAccess_RulesGetResponse":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.APPLICATION_CREDENTIAL_ACCESS_RULES_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "UsersApplication_CredentialsGetResponse":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**keystone_schemas.APPLICATION_CREDENTIALS_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "UsersApplication_CredentialGetResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.APPLICATION_CREDENTIAL_CONTAINER_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "UsersApplication_CredentialsPostRequest":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.APPLICATION_CREDENTIAL_CREATE_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in "UsersApplication_CredentialsPostResponse":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.APPLICATION_CREDENTIAL_CREATE_RESPONSE_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        # ### Identity provider
        elif name == "Os_FederationIdentity_ProvidersGetResponse":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**keystone_schemas.IDENTITY_PROVIDERS_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "Os_FederationIdentity_ProviderGetResponse",
            "Os_FederationIdentity_ProviderPutResponse",
            "Os_FederationIdentity_ProviderPatchResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.IDENTITY_PROVIDER_CONTAINER_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "Os_FederationIdentity_ProviderPutRequest":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**keystone_schemas.IDENTITY_PROVIDER_CREATE_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "Os_FederationIdentity_ProviderPatchRequest":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**keystone_schemas.IDENTITY_PROVIDER_UPDATE_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        # ### Identity provider protocols
        elif name == "Os_FederationIdentity_ProvidersProtocolsGetResponse":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.IDENTITY_PROVIDER_PROTOCOLS_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "Os_FederationIdentity_ProvidersProtocolGetResponse",
            "Os_FederationIdentity_ProvidersProtocolPutResponse",
            "Os_FederationIdentity_ProvidersProtocolPatchResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.IDENTITY_PROVIDER_PROTOCOL_CONTAINER_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "Os_FederationIdentity_ProvidersProtocolPutRequest":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.IDENTITY_PROVIDER_PROTOCOL_CREATE_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "Os_FederationIdentity_ProvidersProtocolPatchRequest":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.IDENTITY_PROVIDER_PROTOCOL_UPDATE_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        # ### Identity provider mapping
        elif name == "Os_FederationMappingsGetResponse":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**keystone_schemas.MAPPINGS_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "Os_FederationMappingGetResponse",
            "Os_FederationMappingPutResponse",
            "Os_FederationMappingPatchResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**keystone_schemas.MAPPING_CONTAINER_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "Os_FederationMappingPutRequest",
            "Os_FederationMappingPatchRequest",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**keystone_schemas.MAPPING_CREATE_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        # ### Identity provider service provider
        elif name == "Os_FederationService_ProvidersGetResponse":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.FEDERATION_SERVICE_PROVIDERS_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "Os_FederationService_ProviderGetResponse",
            "Os_FederationService_ProviderPutResponse",
            "Os_FederationService_ProviderPatchResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.FEDERATION_SERVICE_PROVIDER_CONTAINER_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "Os_FederationService_ProviderPutRequest":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.FEDERATION_SERVICE_PROVIDER_CREATE_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "Os_FederationService_ProviderPatchRequest":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **keystone_schemas.FEDERATION_SERVICE_PROVIDER_UPDATE_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        # SAML2 Metadata
        elif name == "Os_FederationSaml2MetadataGetResponse":
            mime_type = "text/xml"
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    type="string",
                    format="xml",
                    descripion="Identity Provider metadata information in XML format",
                ),
            )
            ref = f"#/components/schemas/{name}"
        # Default
        else:
            (ref, mime_type) = super()._get_schema_ref(
                openapi_spec, name, description, action_name=action_name
            )

        return (ref, mime_type)
