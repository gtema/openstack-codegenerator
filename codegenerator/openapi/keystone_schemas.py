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

from typing import Any

from keystone.application_credential import (
    schema as application_credential_schema,
)
from keystone.assignment import schema as assignment_schema
from keystone.auth import schema as auth_schema
from keystone.identity import schema as identity_schema
from keystone.resource import schema as ks_schema


LINK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Links to the resources in question. See [API Guide / Links and References](https://docs.openstack.org/api-guide/compute/links_and_references.html) for more info.",
    "properties": {
        "href": {"type": "string", "format": "url"},
        "rel": {"type": "string"},
    },
}

LINKS_SCHEMA: dict[str, Any] = {
    "type": "array",
    "description": "Links to the resources in question. See [API Guide / Links and References](https://docs.openstack.org/api-guide/compute/links_and_references.html) for more info.",
    "items": copy.deepcopy(LINK_SCHEMA),
}


PROJECT_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        **ks_schema._project_properties,
    },
    "additionalProperties": True,
}

PROJECT_CONTAINER_SCHEMA = {
    "type": "object",
    "properties": {
        "project": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                **ks_schema._project_properties,
            },
            "additionalProperties": True,
        },
    },
}

PROJECT_CREATE_REQUEST_SCHEMA = {
    "type": "object",
    "properties": {"project": copy.deepcopy(ks_schema.project_create)},
}

PROJECT_UPDATE_REQUEST_SCHEMA = {
    "type": "object",
    "properties": {"project": copy.deepcopy(ks_schema.project_update)},
}


PROJECTS_SCHEMA = {
    "type": "object",
    "properties": {"projects": {"type": "array", "items": PROJECT_SCHEMA}},
}

PROJECT_LIST_PARAMETERS = {
    "domain_id": {
        "in": "query",
        "name": "domain_id",
        "description": "Filters the response by a domain ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
    "enabled": {
        "in": "query",
        "name": "enabled",
        "description": "If set to true, then only enabled projects will be returned. Any value other than 0 (including no value) will be interpreted as true.",
        "schema": {"type": "boolean"},
    },
    "is_domain": {
        "in": "query",
        "name": "is_domain",
        "description": "If this is specified as true, then only projects acting as a domain are included. Otherwise, only projects that are not acting as a domain are included.",
        "schema": {"type": "boolean"},
        "x-openstack": {"min-ver": "3.6"},
    },
    "name": {
        "in": "query",
        "name": "name",
        "description": "Filters the response by a project name.",
        "schema": {"type": "string"},
    },
    "parent_id": {
        "in": "query",
        "name": "parent_id",
        "description": "Filters the response by a parent ID.",
        "schema": {"type": "string", "format": "uuid"},
        "x-openstack": {"min-ver": "3.4"},
    },
}

DOMAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        **ks_schema._domain_properties,
    },
    "additionalProperties": True,
}

DOMAINS_SCHEMA = {
    "type": "object",
    "properties": {"domains": {"type": "array", "items": DOMAIN_SCHEMA}},
}

TAG_SCHEMA = copy.deepcopy(ks_schema._project_tag_name_properties)

TAGS_SCHEMA = {
    "type": "object",
    "properties": {"tags": ks_schema._project_tags_list_properties},
}

ROLE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        "links": {"type": "object"},
        **assignment_schema._role_properties,
    },
}

ROLES_SCHEMA = {
    "type": "object",
    "properties": {
        "roles": {"type": "array", "items": ROLE_SCHEMA},
        "links": {"type": "object"},
    },
}


ROLE_INFERENCE_SCHEMA = {
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

ROLES_INFERENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "role_inference": {
            "properties": {
                "prior_role": ROLE_SCHEMA,
                "implies": {
                    "type": "array",
                    "items": ROLE_SCHEMA,
                },
            }
        }
    },
}

DOMAIN_CONFIG_GROUP_LDAP = {
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

DOMAIN_CONFIG_GROUP_IDENTITY = {
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

DOMAIN_CONFIGS_SCHEMA = {
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

DOMAIN_CONFIG_SCHEMA = {
    "oneOf": [
        DOMAIN_CONFIG_GROUP_IDENTITY,
        DOMAIN_CONFIG_GROUP_LDAP,
    ]
}

USER_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        **identity_schema._user_properties,
    },
}

USERS_SCHEMA = {
    "type": "object",
    "properties": {"projects": {"type": "array", "items": USER_SCHEMA}},
}

GROUP_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        **identity_schema._group_properties,
    },
}

GROUPS_SCHEMA = {
    "type": "object",
    "properties": {"projects": {"type": "array", "items": GROUP_SCHEMA}},
}

# Auth

AUTH_TOKEN_ISSUE_SCHEMA = {
    "type": "object",
    "properties": {"auth": copy.deepcopy(auth_schema.token_issue)},
}

AUTH_PROJECTS_SCHEMA = {
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
                    "links": copy.deepcopy(LINKS_SCHEMA),
                },
            },
        },
        "links": copy.deepcopy(LINKS_SCHEMA),
    },
}

AUTH_DOMAINS_SCHEMA = {
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
                    "links": copy.deepcopy(LINKS_SCHEMA),
                },
            },
        },
        "links": copy.deepcopy(LINKS_SCHEMA),
    },
}

AUTH_SYSTEMS_SCHEMA = {
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
                                    "format": "url",
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

AUTH_USER_INFO_SCHEMA = {
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

AUTH_RECEIPT_SCHEMA = {
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

# Application Credentials
APPLICATION_CREDENTIAL_ACCESS_RULES_SCHEMA = {
    "type": "object",
    "properties": {
        "access_rules": copy.deepcopy(
            application_credential_schema._access_rules_properties
        ),
        "links": copy.deepcopy(LINKS_SCHEMA),
    },
}

APPLICATION_CREDENTIAL_ACCESS_RULE_SCHEMA = copy.deepcopy(
    application_credential_schema._access_rules_properties["items"]
)

APPLICATION_CREDENTIAL_SCHEMA = {
    "type": "object",
    "properties": {
        "project_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the project the application credential was created for and that authentication requests using this application credential will be scoped to.",
        },
        **application_credential_schema._application_credential_properties,
    },
}

APPLICATION_CREDENTIALS_SCHEMA = {
    "type": "object",
    "properties": {
        "application_credentials": {
            "type": "array",
            "items": copy.deepcopy(APPLICATION_CREDENTIAL_SCHEMA),
        },
    },
}
