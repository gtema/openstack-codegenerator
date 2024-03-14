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

from jsonref import replace_refs

from typing import Any

from codegenerator.common.schema import TypeSchema
from codegenerator.openapi.keystone_schemas import common


SCOPE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "The authorization scope, including the system (Since v3.10), a project, or a domain (Since v3.4). If multiple scopes are specified in the same request (e.g. project and domain or domain and system) an HTTP 400 Bad Request will be returned, as a token cannot be simultaneously scoped to multiple authorization targets. An ID is sufficient to uniquely identify a project but if a project is specified by name, then the domain of the project must also be specified in order to uniquely identify the project by name. A domain scope may be specified by either the domain’s ID or name with equivalent results.",
    "properties": {
        "project": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project Name",
                },
                "id": {
                    "type": "string",
                    "description": "Project Id",
                },
                "domain": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Project domain Id",
                        },
                        "name": {
                            "type": "string",
                            "description": "Project domain Name",
                        },
                    },
                },
            },
        },
        "domain": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Domain id",
                },
                "name": {
                    "type": "string",
                    "description": "Domain name",
                },
            },
        },
        "OS-TRUST:trust": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                },
            },
        },
        "system": {
            "type": "object",
            "properties": {
                "all": {"type": "boolean"},
            },
        },
    },
}


AUTH_TOKEN_ISSUE_SCHEMA: dict[str, Any] = replace_refs(
    {
        "type": "object",
        "properties": {
            "auth": {
                "type": "object",
                "description": "An auth object.",
                "properties": {
                    "identity": {
                        "type": "object",
                        "description": "An identity object.",
                        "properties": {
                            "methods": {
                                "type": "array",
                                "description": "The authentication method.",
                                "items": {
                                    "type": "string",
                                    "enum": [
                                        "password",
                                        "token",
                                        "totp",
                                        "application_credential",
                                    ],
                                },
                            },
                            "password": {
                                "type": "object",
                                "description": "The password object, contains the authentication information.",
                                "properties": {
                                    "user": {
                                        "type": "object",
                                        "description": "A `user` object",
                                        "properties": {
                                            "id": {
                                                "type": "string",
                                                "description": "User ID",
                                            },
                                            "name": {
                                                "type": "string",
                                                "description": "User Name",
                                            },
                                            "password": {
                                                "type": "string",
                                                "format": "password",
                                                "description": "User Password",
                                            },
                                            "domain": {
                                                "$ref": "#/definitions/user_domain"
                                            },
                                        },
                                    },
                                },
                            },
                            "token": {
                                "type": "object",
                                "description": "A `token` object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "format": "password",
                                        "description": "Authorization Token value",
                                    },
                                },
                                "required": [
                                    "id",
                                ],
                            },
                            "totp": {
                                "type": "object",
                                "description": "Multi Factor Authentication information",
                                "properties": {
                                    "user": {
                                        "type": "object",
                                        "properties": {
                                            "id": {
                                                "type": "string",
                                                "description": "The user ID",
                                            },
                                            "name": {
                                                "type": "string",
                                                "description": "The user name",
                                            },
                                            "domain": {
                                                "$ref": "#/definitions/user_domain"
                                            },
                                            "passcode": {
                                                "type": "string",
                                                "format": "password",
                                                "description": "MFA passcode",
                                            },
                                        },
                                        "required": ["passcode"],
                                    },
                                },
                                "required": [
                                    "user",
                                ],
                            },
                            "application_credential": {
                                "type": "object",
                                "description": "An application credential object.",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "descripion": "The ID of the application credential used for authentication. If not provided, the application credential must be identified by its name and its owning user.",
                                    },
                                    "name": {
                                        "type": "string",
                                        "descripion": "The name of the application credential used for authentication. If provided, must be accompanied by a user object.",
                                    },
                                    "secret": {
                                        "type": "string",
                                        "format": "password",
                                        "description": "The secret for authenticating the application credential.",
                                    },
                                    "user": {
                                        "type": "object",
                                        "description": "A user object, required if an application credential is identified by name and not ID.",
                                        "properties": {
                                            "id": {
                                                "type": "string",
                                                "description": "The user ID",
                                            },
                                            "name": {
                                                "type": "string",
                                                "description": "The user name",
                                            },
                                            "domain": {
                                                "$ref": "#/definitions/user_domain"
                                            },
                                        },
                                    },
                                },
                                "required": ["secret"],
                            },
                        },
                        "required": [
                            "methods",
                        ],
                    },
                    "scope": SCOPE_SCHEMA,
                },
                "required": [
                    "identity",
                ],
            },
        },
        "definitions": {
            "user_domain": {
                "type": "object",
                "description": "User Domain object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "User Domain ID",
                    },
                    "name": {
                        "type": "string",
                        "description": "User Domain Name",
                    },
                },
            },
        },
    },
    proxies=False,
)

AUTH_PROJECTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "domain_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "The ID of the domain for the project.",
                    },
                    "id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "The ID of the project.",
                    },
                    "name": {
                        "type": "string",
                        "description": "The name of the project",
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "If set to true, project is enabled. If set to false, project is disabled.",
                    },
                    "links": copy.deepcopy(common.LINKS_SCHEMA),
                },
            },
        },
        "links": copy.deepcopy(common.LINKS_SCHEMA),
    },
}

AUTH_DOMAINS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "domains": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "The ID of the domain.",
                    },
                    "name": {
                        "type": "string",
                        "description": "The name of the domain",
                    },
                    "description": {
                        "type": "string",
                        "description": "The description of the domain.",
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "If set to true, domain is enabled. If set to false, domain is disabled.",
                    },
                    "links": copy.deepcopy(common.LINKS_SCHEMA),
                },
            },
        },
        "links": copy.deepcopy(common.LINKS_SCHEMA),
    },
}

AUTH_SYSTEMS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "system": {
            "type": "array",
            "description": "A list of systems to access based on role assignments.",
            "items": {
                "type": "object",
                "additionalProperties": {"type": "boolean"},
            },
        }
    },
}

AUTH_CATALOG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "catalog": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "endpoints": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "format": "uuid",
                                    "description": "The endpoint UUID",
                                },
                                "interface": {
                                    "type": "string",
                                    "enum": ["public", "internal", "admin"],
                                },
                                "region": {
                                    "type": "string",
                                    "description": "Region name of the endpoint",
                                },
                                "url": {
                                    "type": "string",
                                    "format": "uri",
                                    "description": "The endpoint url",
                                },
                            },
                        },
                    },
                    "id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "The UUID of the service to which the endpoint belongs.",
                    },
                    "type": {
                        "type": "string",
                        "description": "The service type, which describes the API implemented by the service",
                    },
                    "name": {
                        "type": "string",
                        "description": "The service name.",
                    },
                },
            },
        }
    },
}

AUTH_USER_INFO_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "A user object",
    "properties": {
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "A user UUID",
        },
        "name": {"type": "string", "description": "A user name"},
        "domain": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "A user domain UUID",
                },
                "name": {
                    "type": "string",
                    "description": "A user domain name",
                },
            },
        },
        "password_expires_at": {
            "type": "string",
            "format": "date-time",
            "description": "DateTime of the user password expiration",
        },
        "OS-FEDERATION": {"type": "object"},
    },
}

AUTH_TOKEN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "token": {
            "type": "object",
            "properties": {
                "audit_ids": {
                    "type": "array",
                    "description": "A list of one or two audit IDs. An audit ID is a unique, randomly generated, URL-safe string that you can use to track a token. The first audit ID is the current audit ID for the token. The second audit ID is present for only re-scoped tokens and is the audit ID from the token before it was re-scoped. A re- scoped token is one that was exchanged for another token of the same or different scope. You can use these audit IDs to track the use of a token or chain of tokens across multiple requests and endpoints without exposing the token ID to non-privileged users.",
                    "items": {"type": "string"},
                },
                "catalog": {
                    "description": "A catalog object.",
                    **AUTH_CATALOG_SCHEMA["properties"]["catalog"],
                },
                "expires_at": {
                    "type": "string",
                    "format": "date-time",
                    "description": "The date and time when the token expires.",
                },
                "issues_at": {
                    "type": "string",
                    "format": "date-time",
                    "description": "The date and time when the token was issued.",
                },
                "methods": {
                    "type": "array",
                    "description": "The authentication methods, which are commonly password, token, or other methods. Indicates the accumulated set of authentication methods that were used to obtain the token. For example, if the token was obtained by password authentication, it contains password. Later, if the token is exchanged by using the token authentication method one or more times, the subsequently created tokens contain both password and token in their methods attribute. Unlike multi-factor authentication, the methods attribute merely indicates the methods that were used to authenticate the user in exchange for a token. The client is responsible for determining the total number of authentication factors.",
                    "items": {"type": "string"},
                },
                "user": copy.deepcopy(AUTH_USER_INFO_SCHEMA),
            },
        }
    },
}

AUTH_SCOPED_TOKEN_SCHEMA: dict[str, Any] = copy.deepcopy(AUTH_TOKEN_SCHEMA)
AUTH_SCOPED_TOKEN_SCHEMA["properties"]["token"]["properties"].update(
    **{
        "is_domain": {
            "type": "boolean",
        },
        "domain": {
            "type": "object",
            "description": "A domain object including the id and name representing the domain the token is scoped to. This is only included in tokens that are scoped to a domain.",
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "A domain UUID",
                },
                "name": {
                    "type": "string",
                    "description": "A domain name",
                },
            },
        },
        "project": {
            "type": "object",
            "description": "A project object including the id, name and domain object representing the project the token is scoped to. This is only included in tokens that are scoped to a project.",
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "A user domain UUID",
                },
                "name": {
                    "type": "string",
                    "description": "A user domain name",
                },
            },
        },
        "roles": {
            "type": "array",
            "description": "A list of role objects",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "A role UUID",
                    },
                    "name": {
                        "type": "string",
                        "description": "A role name",
                    },
                },
            },
        },
        "system": {
            "type": "object",
            "description": 'A system object containing information about which parts of the system the token is scoped to. If the token is scoped to the entire deployment system, the system object will consist of {"all": true}. This is only included in tokens that are scoped to the system.',
            "additionalProperties": {"type": "boolean"},
        },
    }
)

AUTH_RECEIPT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "receipt": {
            "type": "object",
            "properties": {
                "expires_at": {
                    "type": "string",
                    "format": "date-time",
                    "description": "The date and time when the token expires.",
                },
                "issues_at": {
                    "type": "string",
                    "format": "date-time",
                    "description": "The date and time when the token was issued.",
                },
                "methods": {
                    "type": "array",
                    "description": "The authentication methods, which are commonly password, token, or other methods. Indicates the accumulated set of authentication methods that were used to obtain the token. For example, if the token was obtained by password authentication, it contains password. Later, if the token is exchanged by using the token authentication method one or more times, the subsequently created tokens contain both password and token in their methods attribute. Unlike multi-factor authentication, the methods attribute merely indicates the methods that were used to authenticate the user in exchange for a token. The client is responsible for determining the total number of authentication factors.",
                    "items": {"type": "string"},
                },
                "user": copy.deepcopy(AUTH_USER_INFO_SCHEMA),
            },
        },
        "required_auth_methods": {
            "type": "array",
            "items": {"type": "string"},
            "description": "A list of authentication rules that may be used with the auth receipt to complete the authentication process.",
        },
    },
}


def _post_process_operation_hook(
    openapi_spec, operation_spec, path: str | None = None
):
    """Hook to allow service specific generator to modify details"""
    operationId = operation_spec.operationId

    if operationId == "auth/tokens:post":
        (receipt_schema_ref, receipt_mime_type, matched) = _get_schema_ref(
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


def _get_schema_ref(
    openapi_spec,
    name,
    description=None,
    schema_def=None,
    action_name=None,
) -> tuple[str | None, str | None, bool]:
    mime_type: str = "application/json"
    ref: str

    # Auth
    if name == "AuthTokensPostRequest":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**AUTH_TOKEN_ISSUE_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name in ["AuthTokensGetResponse", "AuthTokensPostResponse"]:
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**AUTH_SCOPED_TOKEN_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name == "AuthReceiptSchema":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**AUTH_RECEIPT_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "AuthProjectsGetResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**AUTH_PROJECTS_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "AuthDomainsGetResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**AUTH_DOMAINS_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name == "AuthSystemGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**AUTH_SYSTEMS_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name == "AuthCatalogGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**AUTH_CATALOG_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"

    else:
        return (None, None, False)

    return (ref, mime_type, True)
