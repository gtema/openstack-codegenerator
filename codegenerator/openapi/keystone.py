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
from keystone.auth import schema as auth_schema
from keystone.identity import schema as identity_schema
from keystone.resource import schema as ks_schema

from codegenerator.common.schema import ParameterSchema
from codegenerator.common.schema import PathSchema
from codegenerator.common.schema import SpecSchema
from codegenerator.common.schema import TypeSchema
from codegenerator.openapi.base import OpenStackServerSourceBase
from codegenerator.openapi.utils import merge_api_ref_doc


PROJECT_SCHEMA = TypeSchema(
    type="object",
    properties={
        "id": {"type": "string", "format": "uuid"},
        **ks_schema._project_properties,
    },
    additionalProperties=True,
)

PROJECTS_SCHEMA = TypeSchema(
    type="object",
    properties={"projects": {"type": "array", "items": PROJECT_SCHEMA}},
)

DOMAIN_SCHEMA = TypeSchema(
    **{
        "type": "object",
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            **ks_schema._domain_properties,
        },
        "additionalProperties": True,
    }
)

DOMAINS_SCHEMA = TypeSchema(
    **{
        "type": "object",
        "properties": {"domains": {"type": "array", "items": DOMAIN_SCHEMA}},
    }
)

TAG_SCHEMA = TypeSchema(**ks_schema._project_tag_name_properties)

TAGS_SCHEMA = TypeSchema(
    **{
        "type": "object",
        "properties": {"tags": ks_schema._project_tags_list_properties},
    }
)

ROLE_SCHEMA = TypeSchema(
    **{
        "type": "object",
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "links": {"type": "object"},
            **assignment_schema._role_properties,
        },
    }
)

ROLES_SCHEMA = TypeSchema(
    **{
        "type": "object",
        "properties": {
            "roles": {"type": "array", "items": ROLE_SCHEMA},
            "links": {"type": "object"},
        },
    }
)


ROLE_INFERENCE_SCHEMA = TypeSchema(
    **{
        "type": "object",
        "properties": {
            "role_inference": {
                "properties": {
                    "prior_role": ROLE_SCHEMA,
                    "implies": ROLE_SCHEMA,
                }
            }
        },
    }
)
ROLES_INFERENCE_SCHEMA = TypeSchema(
    **{
        "type": "object",
        "properties": {
            "role_inference": {
                "properties": {
                    "prior_role": ROLE_SCHEMA,
                    "implies": {
                        "type": "array",
                        "item": ROLE_SCHEMA,
                    },
                }
            }
        },
    }
)

DOMAIN_CONFIG_GROUP_LDAP = TypeSchema(
    **{
        "type": "object",
        "description": "An ldap object. Required to set the LDAP group configuration options.",
        "properties": {
            "url": {
                "type": "string",
                "format": "url",
                "description": "The LDAP URL.",
            },
            "user_tree_dn": {
                "type": "string",
                "description": "The base distinguished name (DN) of LDAP, from where all users can be reached. For example, ou=Users,dc=root,dc=org.",
            },
        },
        "additionalProperties": True,
    }
)

DOMAIN_CONFIG_GROUP_IDENTITY = TypeSchema(
    **{
        "type": "object",
        "description": "An identity object.",
        "properties": {
            "driver": {
                "type": "string",
                "description": "The Identity backend driver.",
            },
        },
        "additionalProperties": True,
    }
)

DOMAIN_CONFIGS_SCHEMA = TypeSchema(
    **{
        "type": "object",
        "properties": {
            "config": {
                "type": "object",
                "description": "A config object.",
                "properties": {
                    "identity": DOMAIN_CONFIG_GROUP_IDENTITY,
                    "ldap": DOMAIN_CONFIG_GROUP_LDAP,
                },
            }
        },
    }
)
DOMAIN_CONFIG_SCHEMA = TypeSchema(
    **{
        "oneOf": [
            DOMAIN_CONFIG_GROUP_IDENTITY,
            DOMAIN_CONFIG_GROUP_LDAP,
        ]
    }
)

USER_SCHEMA = TypeSchema(
    **{
        "type": "object",
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            **identity_schema._user_properties,
        },
    }
)

USERS_SCHEMA = TypeSchema(
    **{
        "type": "object",
        "properties": {"projects": {"type": "array", "items": USER_SCHEMA}},
    }
)

GROUP_SCHEMA = TypeSchema(
    **{
        "type": "object",
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            **identity_schema._group_properties,
        },
    }
)

GROUPS_SCHEMA = TypeSchema(
    **{
        "type": "object",
        "properties": {"projects": {"type": "array", "items": GROUP_SCHEMA}},
    }
)


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
            raise RuntimeError("Error generating Keystone OpenAPI schma")
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
                    },
                    parameters={
                        "X-Auth-Token": {
                            "in": "header",
                            "name": "X-Auth-Token",
                            "description": "A valid authentication token",
                            "schema": {"type": "string", "format": "secret"},
                        },
                    },
                ),
            )

        for route in self.router.iter_rules():
            if route.rule.startswith("/static"):
                continue
            # if not route.rule.startswith("/v3/domains"):
            #    continue
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

            schema_ref = self._get_schema_ref(
                openapi_spec,
                schema_name,
                description=f"Request of the {operation_spec.operationId} operation",
            )

            if schema_ref:
                content = operation_spec.requestBody = {"content": {}}
                mime_type = "application/json"
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
        rsp = responses_spec.setdefault(response_code, dict(description="Ok"))
        if response_code != "204" and method not in ["DELETE", "HEAD"]:
            # Arrange response placeholder
            schema_name = (
                "".join([x.title() for x in path_resource_names])
                + method.title()
                + "Response"
            )
            schema_ref = self._get_schema_ref(
                openapi_spec,
                schema_name,
                description=f"Response of the {operation_spec.operationId} operation",
            )

            if schema_ref:
                rsp["content"] = {
                    "application/json": {"schema": {"$ref": schema_ref}}
                }

        if path == "/v3/auth/tokens":
            rsp_headers = rsp.setdefault("headers", {})
            openapi_spec.components.headers["X-Subject-Token"] = {
                "description": "API Authorization token",
                "schema": {"type": "string"},
            }
            openapi_spec.components.parameters[
                "X-Subject-Token"
            ] = ParameterSchema(
                location="header",
                name="X-Subject-Token",
                description="The authentication token to be verified.",
                type_schema={"type": "string"},
                required=True,
            )
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
                    ParameterSchema(ref="#/components/parameters/X-Auth-Token")
                )
                operation_spec.parameters.append(
                    ParameterSchema(
                        ref="#/components/parameters/X-Subject-Token"
                    )
                )
                rsp_headers.setdefault(
                    "X-Subject-Token",
                    {"$ref": "#/components/headers/X-Subject-Token"},
                )

    def _get_tags_for_url(self, url):
        """Return Tag (group) name based on the URL"""
        pass

        # for part in route.rule.split("/"):
        #    if not part:
        #        continue
        #    if part.startswith("<"):
        #        param = part.strip("<>").split(":")
        #        path_elements.append("{" + param[-1] + "}")
        #    else:
        #        if not tag_name and part != "" and part != "v3":
        #            tag_name = part
        #        path_elements.append(part)

        # if not tag_name:
        #    tag_name = "versions"

    def _get_schema_ref(
        self,
        openapi_spec,
        name,
        description=None,
        schema_def=None,
        action_name=None,
    ):
        # Projects
        if name == "ProjectsPostRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**ks_schema.project_create)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectsPostResponse":
            openapi_spec.components.schemas.setdefault(name, PROJECT_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectPatchRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**ks_schema.project_update)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectPatchResponse":
            openapi_spec.components.schemas.setdefault(name, PROJECT_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectsGetResponse":
            openapi_spec.components.schemas.setdefault(name, PROJECTS_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectGetResponse":
            openapi_spec.components.schemas.setdefault(name, PROJECT_SCHEMA)
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
            openapi_spec.components.schemas.setdefault(name, TAGS_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectsTagsPutResponse":
            openapi_spec.components.schemas.setdefault(name, TAGS_SCHEMA)
            ref = f"#/components/schemas/{name}"

        # Project/Domain Roles
        elif name == "ProjectsUsersRolesGetResponse":
            openapi_spec.components.schemas.setdefault(name, ROLES_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "ProjectsGroupsRolesGetResponse":
            openapi_spec.components.schemas.setdefault(name, ROLES_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "DomainsUsersRolesGetResponse":
            openapi_spec.components.schemas.setdefault(name, ROLES_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "DomainsGroupsRolesGetResponse":
            openapi_spec.components.schemas.setdefault(name, ROLES_SCHEMA)
            ref = f"#/components/schemas/{name}"

        # Domains
        elif name == "DomainsPostRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**ks_schema.domain_create)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "DomainsPostResponse":
            openapi_spec.components.schemas.setdefault(name, DOMAIN_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "DomainPatchRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**ks_schema.domain_update)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "DomainPatchResponse":
            openapi_spec.components.schemas.setdefault(name, DOMAIN_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "DomainsGetResponse":
            openapi_spec.components.schemas.setdefault(name, DOMAINS_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "DomainGetResponse":
            openapi_spec.components.schemas.setdefault(name, DOMAIN_SCHEMA)
            ref = f"#/components/schemas/{name}"

        # Users
        elif name == "UserPatchRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**identity_schema.user_update)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "UsersPostRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**identity_schema.user_create)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "UserPatchResponse":
            openapi_spec.components.schemas.setdefault(name, USER_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "UsersGetResponse":
            openapi_spec.components.schemas.setdefault(name, USERS_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "UserGetResponse":
            openapi_spec.components.schemas.setdefault(name, USER_SCHEMA)
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
            openapi_spec.components.schemas.setdefault(name, GROUP_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "GroupsGetResponse":
            openapi_spec.components.schemas.setdefault(name, GROUPS_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "GroupGetResponse":
            openapi_spec.components.schemas.setdefault(name, GROUP_SCHEMA)
            ref = f"#/components/schemas/{name}"

        # Roles
        elif name == "RolesGetResponse":
            openapi_spec.components.schemas.setdefault(name, ROLES_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "RolesPostRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**assignment_schema.role_create)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "RolesPostResponse":
            openapi_spec.components.schemas.setdefault(name, ROLE_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "RoleGetResponse":
            openapi_spec.components.schemas.setdefault(name, ROLE_SCHEMA)
            ref = f"#/components/schemas/{name}"
        elif name == "RolePatchRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**assignment_schema.role_update)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "RolePatchResponse":
            openapi_spec.components.schemas.setdefault(name, ROLE_SCHEMA)
            ref = f"#/components/schemas/{name}"

        # Role Implies
        elif name == "RolesImpliesGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, ROLES_INFERENCE_SCHEMA
            )
            ref = f"#/components/schemas/{name}"
        elif name == "RolesImplyGetResponse":
            openapi_spec.components.schemas.setdefault(
                name, ROLE_INFERENCE_SCHEMA
            )
            ref = f"#/components/schemas/{name}"
        elif name == "RolesImplyPutResponse":
            openapi_spec.components.schemas.setdefault(
                name, ROLE_INFERENCE_SCHEMA
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
                name, DOMAIN_CONFIGS_SCHEMA
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
                name, DOMAIN_CONFIG_SCHEMA
            )
            ref = f"#/components/schemas/{name}"
        elif name == "AuthTokensPostRequest":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**auth_schema.token_issue)
            )
            ref = f"#/components/schemas/{name}"
        else:
            ref = super()._get_schema_ref(
                openapi_spec, name, description, action_name=action_name
            )

        return ref
