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
import logging
from multiprocessing import Process, Manager
from pathlib import Path
import re
import tempfile
from typing import Any

from routes.base import Route
from ruamel.yaml.scalarstring import LiteralScalarString

import sqlalchemy

from codegenerator.common.schema import ParameterSchema
from codegenerator.common.schema import PathSchema
from codegenerator.common.schema import SpecSchema
from codegenerator.common.schema import TypeSchema
from codegenerator.openapi.base import OpenStackServerSourceBase
from codegenerator.openapi.base import VERSION_RE
from codegenerator.openapi import neutron_schemas
from codegenerator.openapi.utils import merge_api_ref_doc


PASTE_CONFIG = """
[composite:neutron]
use = egg:Paste#urlmap
# /: neutronversions_composite
/v2.0: neutronapi_v2_0

[composite:neutronapi_v2_0]
use = call:neutron.auth:pipeline_factory
keystone = extensions neutronapiapp_v2_0

[composite:neutronversions_composite]
use = call:neutron.auth:pipeline_factory
keystone = neutronversions

[filter:extensions]
paste.filter_factory = neutron.api.extensions:plugin_aware_extension_middleware_factory

[app:neutronversions]
paste.app_factory = neutron.pecan_wsgi.app:versions_factory

[app:neutronapiapp_v2_0]
paste.app_factory = neutron.api.v2.router:APIRouter.factory
    """


class NeutronGenerator(OpenStackServerSourceBase):
    URL_TAG_MAP = {
        "/agents/{agent_id}/dhcp-networks": "dhcp-agent-scheduler",
        "/agents": "networking-agents",
        "/ports/{port_id}/bindings": "port-bindings",
        "/routers/{router_id}/conntrack_helpers/": "routers-conntrack-helper",
        "/floatingips/{floatingip_id}/port_forwardings/": "floatingips-port-forwardings",
    }

    def __init__(self):
        self.api_version = "2.0"
        self.min_api_version = "2.0"

        # self.tempdir = tempfile.gettempdir()

    def _build_neutron_db(self, tempdir):
        db_path: str = f"sqlite:///{tempdir}/neutron.db"  # noqa
        engine = sqlalchemy.create_engine(db_path)
        from neutron.db.migration.models import head

        db_meta = head.get_metadata()
        db_meta.create_all(engine)
        return (db_path, engine)

    def process_base_neutron_routes(self, work_dir, processed_routes, args):
        """Setup base Neutron with whatever is in the core"""
        logging.info("Processing base Neutron")
        # Create the default configurations
        from neutron.common import config as neutron_config
        from neutron.conf.plugins.ml2 import config as ml2_config

        from neutron.db import models  # noqa
        from neutron_lib import fixture
        from oslo_config import cfg
        from oslo_db import options as db_options

        tempdir = tempfile.gettempdir()

        fixture.RPCFixture().setUp()

        neutron_config.register_common_config_options()
        ml2_config.register_ml2_plugin_opts()

        plugin = "neutron.plugins.ml2.plugin.Ml2Plugin"
        cfg.CONF.set_override("core_plugin", plugin)

        cfg.CONF.set_override(
            "api_paste_config", Path(tempdir, "api-paste.ini.generator")
        )
        with open(Path(tempdir, "api-paste.ini.generator"), "w") as fp:
            fp.write(PASTE_CONFIG)

        neutron_config.init([])
        cfg.CONF.set_override(
            "service_plugins",
            [
                "router",
                "metering",
                "qos",
                "tag",
                "flavors",
                "auto_allocate",
                "segments",
                "network_ip_availability",
                "network_segment_range",
                "revisions",
                "timestamp",
                "loki",
                "log",
                "port_forwarding",
                "placement",
                "conntrack_helper",
                # "ovn-router",
                # "trunk",
                "local_ip",
                "ndp_proxy",
            ],
        )
        cfg.CONF.set_override(
            "extension_drivers",
            [
                "dns",
                "port_security",
                "qos",
                "data_plane_status",
                "dns_domain_ports",
                "dns_domain_keywords",
                "port_device_profile",
                "port_numa_affinity_policy",
                "uplink_status_propagation",
                "subnet_dns_publis_fixed_ip",
                "tag_ports_during_bulk_creation",
                "uplink_status_propagation",
                "port_hints",
                "port_device_profile",
                "port_hint_ovs_tx_steering",
            ],
            group="ml2",
        )

        # Create the DB
        db_path, engine = self._build_neutron_db(tempdir)
        db_options.set_defaults(cfg.CONF, connection=db_path)

        app_ = neutron_config.load_paste_app("neutron")
        router = None
        for i, w in app_.applications:
            if hasattr(w, "_router"):
                # We are only interested in the extensions app with a router
                router = w._router

        # Raise an error to signal that we have not found a router
        if not router:
            raise NotImplementedError

        (impl_path, openapi_spec) = self._read_spec(work_dir)
        self._process_router(router, openapi_spec, processed_routes)

        # Add base resource routes exposed as a pecan app
        self._process_base_resource_routes(openapi_spec, processed_routes)

        self.dump_openapi(openapi_spec, impl_path, args.validate)

    def process_neutron_with_vpnaas(self, work_dir, processed_routes, args):
        """Setup base Neutron with enabled vpnaas"""
        logging.info("Processing Neutron with VPNaaS")
        from neutron.common import config as neutron_config
        from neutron.conf.plugins.ml2 import config as ml2_config

        from neutron.db import models  # noqa
        from neutron_lib import fixture
        from neutron import manager  # noqa
        from oslo_config import cfg
        from oslo_db import options as db_options

        fixture.RPCFixture().setUp()
        tempdir = tempfile.gettempdir()

        neutron_config.register_common_config_options()
        ml2_config.register_ml2_plugin_opts()

        plugin = "neutron.plugins.ml2.plugin.Ml2Plugin"
        cfg.CONF.set_override("core_plugin", plugin)

        cfg.CONF.set_override(
            "api_paste_config", Path(tempdir, "api-paste.ini.generator")
        )
        with open(Path(tempdir, "api-paste.ini.generator"), "w") as fp:
            fp.write(PASTE_CONFIG)

        neutron_config.init([])
        cfg.CONF.set_override(
            "service_plugins",
            [
                "router",
                "vpnaas",
            ],
        )
        cfg.CONF.set_override(
            "service_provider",
            [
                "VPN:dummy:neutron_vpnaas.tests.unit.dummy_ipsec.DummyIPsecVPNDriver:default",
            ],
            group="service_providers",
        )
        # Create the DB
        db_path, engine = self._build_neutron_db(tempdir)
        db_options.set_defaults(cfg.CONF, connection=db_path)

        # Create VPNaaS DB tables
        from neutron_vpnaas.db.models import head

        db_meta = head.get_metadata()
        db_meta.create_all(engine)

        app_ = neutron_config.load_paste_app("neutron")
        for i, w in app_.applications:
            if hasattr(w, "_router"):
                # We are only interested in the extensions app with a router
                router = w._router

        # Raise an error to signal that we have not found a router
        if not router:
            raise NotImplementedError

        (impl_path, openapi_spec) = self._read_spec(work_dir)
        self._process_router(router, openapi_spec, processed_routes)
        self.dump_openapi(openapi_spec, impl_path, args.validate)

    def _read_spec(self, work_dir):
        """Read the spec from file or create an empty one"""
        impl_path = Path(work_dir, "openapi_specs", "network", "v2.yaml")
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        openapi_spec = self.load_openapi(Path(impl_path))
        if not openapi_spec:
            openapi_spec = SpecSchema(
                info=dict(
                    title="OpenStack Network API",
                    description=LiteralScalarString(
                        "Network API provided by Neutron service"
                    ),
                    version=self.api_version,
                ),
                openapi="3.1.0",
                security=[{"ApiKeyAuth": []}],
                tags=[],
                paths={},
                components=dict(
                    securitySchemes={
                        "ApiKeyAuth": {
                            "type": "apiKey",
                            "in": "header",
                            "name": "X-Auth-Token",
                        }
                    },
                    headers={},
                    parameters={},
                    schemas={},
                ),
            )
        return (impl_path, openapi_spec)

    def generate(self, target_dir, args):
        work_dir = Path(target_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        # NOTE(gtema): call me paranoic or stupid, but I just gave up fighting
        # agains oslo_config and oslo_policy with their global state. It is
        # just too painful and takes too much precious time. On multiple
        # invocation with different config there are plenty of things remaining
        # in the old state. In order to workaroung this just process in
        # different processes.
        with Manager() as manager:
            # Since we may process same route multiple times we need to have a
            # shared state
            processed_routes = manager.dict()
            # Base Neutron
            p = Process(
                target=self.process_base_neutron_routes,
                args=[work_dir, processed_routes, args],
            )
            p.start()
            p.join()
            if p.exitcode != 0:
                raise RuntimeError("Error generating Neutron OpenAPI schma")

            # VPNaaS
            p = Process(
                target=self.process_neutron_with_vpnaas,
                args=[work_dir, processed_routes, args],
            )
            p.start()
            p.join()
            if p.exitcode != 0:
                raise RuntimeError("Error generating Neutron OpenAPI schma")

        (impl_path, openapi_spec) = self._read_spec(work_dir)

        # post processing cleanup of the spec
        self._sanitize_param_ver_info(openapi_spec, self.min_api_version)

        # merge descriptions from api-ref doc
        if args.api_ref_src:
            merge_api_ref_doc(
                openapi_spec, args.api_ref_src, allow_strip_version=False
            )

        self.dump_openapi(openapi_spec, Path(impl_path), args.validate)

        return impl_path

    def _process_router(self, router, openapi_spec, processed_routes):
        """Scan through the routes exposed on a router"""
        for route in router.mapper.matchlist:
            if route.routepath.endswith(".:(format)"):
                continue
            # if route.routepath != "/networks":
            #    continue
            # if "networks" not in route.routepath:
            #    continue
            if route.routepath.endswith("/edit") or route.routepath.endswith(
                "/new"
            ):
                # NEUTRON folks - please fix
                logging.warning(
                    "Skipping processing %s route", route.routepath
                )
                continue
            if (
                "/qos/ports" in route.routepath
                or "/qos/networks" in route.routepath
            ):
                # NEUTRON folks - please fix
                logging.warning(
                    "Skipping processing %s route", route.routepath
                )
                continue
            if (
                route.routepath.endswith("/tags")
                and route.conditions["method"][0] == "POST"
            ):
                logging.warning(
                    "Skipping processing POST %s route", route.routepath
                )
                continue
            if route.routepath.startswith("/extensions") and route.conditions[
                "method"
            ][0] in ["POST", "DELETE", "PUT"]:
                continue
            if route.routepath.startswith(
                "/availability_zones"
            ) and route.conditions["method"][0] in ["POST", "DELETE", "PUT"]:
                continue
            if route.routepath.startswith(
                "/availability_zones/"
            ) and route.conditions["method"][0] in ["GET"]:
                # There is no "show" for AZ
                continue
            if route.routepath in ["/quotas/tenant", "/quotas/project"]:
                # Tenant and Project quota are not a thing
                continue
            if route.routepath == "/quotas" and route.conditions["method"][
                0
            ] in ["POST"]:
                # Tenant and Project quota is the same
                continue

            self._process_route(route, openapi_spec, processed_routes)

    def _process_base_resource_routes(self, openapi_spec, processed_routes):
        """Process base resources exposed through Pecan"""
        from neutron import manager

        mgr = manager.NeutronManager.get_instance()
        # Nets/subnets/ports are base resources (non extension). They are thus
        # missing in the extension middleware
        for coll, res in [
            ("networks", "network"),
            ("subnets", "subnet"),
            ("ports", "port"),
        ]:
            for method, action in [("GET", "index"), ("POST", "create")]:
                self._process_route(
                    Route(
                        coll,
                        f"/{coll}",
                        conditions={"method": [method]},
                        action=action,
                        _collection_name=coll,
                        _member_name=res,
                    ),
                    openapi_spec,
                    processed_routes,
                    controller=mgr.get_controller_for_resource(coll),
                )
        for coll, res in [
            ("networks", "network"),
            ("subnets", "subnet"),
            ("ports", "port"),
        ]:
            for method, action in [
                ("GET", "show"),
                ("DELETE", "delete"),
                ("PUT", "update"),
            ]:
                self._process_route(
                    Route(
                        coll,
                        f"/{coll}/{{{res}_id}}",
                        conditions={"method": [method]},
                        action=action,
                        _collection_name=coll,
                        _member_name=res,
                    ),
                    openapi_spec,
                    processed_routes,
                    controller=mgr.get_controller_for_resource(coll),
                )
        self._process_route(
            Route(
                "port_allowed_address_pair",
                "/ports/{port_id}/add_allowed_address_pairs",
                conditions={"method": ["PUT"]},
                action="add_allowed_address_pairs",
                _collection_name=coll,
                _member_name=res,
            ),
            openapi_spec,
            processed_routes,
            controller=mgr.get_controller_for_resource("ports"),
        )

    def _process_route(
        self,
        route,
        openapi_spec,
        processed_routes,
        controller=None,
        ver_prefix="/v2.0",
    ):
        path = ver_prefix
        operation_spec = None
        for part in route.routelist:
            if isinstance(part, dict):
                path += "{" + part["name"] + "}"
            else:
                path += part

        if "method" not in route.conditions:
            raise RuntimeError("Method not set for %s" % route)
        method = (
            route.conditions.get("method", "GET")[0]
            if route.conditions
            else "GET"
        )

        wsgi_controller = controller or route.defaults["controller"]
        # collection_name = route.collection_name
        # member_name = route.member_name
        action = route.defaults["action"]
        controller = None
        func = None
        if hasattr(wsgi_controller, "controller"):
            controller = wsgi_controller.controller
            if hasattr(wsgi_controller, "func"):
                func = wsgi_controller.func
        else:
            controller = wsgi_controller
            if hasattr(wsgi_controller, action):
                func = getattr(wsgi_controller, action)

        processed_key = f"{path}:{method}:{action}"  # noqa
        # Some routes in Neutron are duplicated. We need to skip them since
        # otherwise we may duplicate query parameters which are just a list
        if processed_key not in processed_routes:
            processed_routes[processed_key] = 1
        else:
            logging.warning("Skipping duplicated route %s", processed_key)
            return

        logging.info(
            "Path: %s; method: %s; operation: %s", path, method, action
        )

        # Get Path elements
        path_elements: list[str] = list(filter(None, path.split("/")))
        if path_elements and VERSION_RE.match(path_elements[0]):
            path_elements.pop(0)

        operation_tags = self._get_tags_for_url(path)

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
                if global_param_name == "_project_id":
                    global_param_name = "project_id"
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
                # openapi_spec.components["parameters"].setdefault(global_param_name, dict())
                if not path_param.description:
                    path_param.description = (
                        f"{param_name} parameter for {path} API"
                    )
                # We can only assume the param type. For path it is logically a string only
                path_param.type_schema = TypeSchema(type="string")
                openapi_spec.components.parameters[global_param_name] = (
                    path_param
                )
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

        # Set operationId
        operation_id = re.sub(
            r"^(/?v[0-9.]*/)",
            "",
            "/".join([x.strip("{}") for x in path_elements])
            + f":{method.lower()}",  # noqa
        )

        path_spec = openapi_spec.paths.setdefault(
            path, PathSchema(parameters=path_params)
        )
        operation_spec = getattr(path_spec, method.lower())
        if not operation_spec.operationId:
            operation_spec.operationId = operation_id
        operation_spec.tags.extend(operation_tags)
        operation_spec.tags = list(set(operation_spec.tags))
        for tag in operation_tags:
            if tag not in [x["name"] for x in openapi_spec.tags]:
                openapi_spec.tags.append({"name": tag})

        self.process_operation(
            func,
            openapi_spec,
            operation_spec,
            path_resource_names,
            controller=controller,
            operation_name=action,
            path=path,
            method=method,
        )

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
        path=None,
    ):
        logging.info(
            "Operation: %s",
            operation_name,
        )

        attr_info = getattr(controller, "_attr_info", {})
        collection = getattr(controller, "_collection", None)
        resource = getattr(controller, "_resource", None)
        # Some backup locations for non extension like controller
        if not attr_info:
            attr_info = getattr(controller, "resource_info", {})
        if not collection:
            collection = getattr(controller, "collection", None)
        if not resource:
            resource = getattr(controller, "resource", None)

        # body_schema_name = None
        if method in ["POST", "PUT"]:
            # Modification methods requires Body
            schema_name = (
                "".join([x.title() for x in path_resource_names])
                + operation_name.title()
                + "Request"
            )

            schema_ref = self._get_schema_ref(
                openapi_spec,
                schema_name,
                description=f"Request of the {operation_spec.operationId} operation",
                schema_def=attr_info,
                method=method,
                collection_key=collection,
                resource_key=resource,
                operation=operation_name,
            )

            if schema_ref:
                content = operation_spec.requestBody.setdefault("content", {})
                mime_type = "application/json"
                content[mime_type] = {"schema": {"$ref": schema_ref}}

        if operation_name == "index":
            # Build query params
            for field, data in attr_info.items():
                # operation_spec.setdefault("parameters", [])
                if data.get("is_filter", False):
                    global_param_name = f"{collection}_{field}".replace(
                        ":", "_"
                    )
                    param_ref_name = (
                        f"#/components/parameters/{global_param_name}"
                    )
                    # Ensure global parameter is present
                    query_param = (
                        openapi_spec.components.parameters.setdefault(
                            global_param_name,
                            ParameterSchema(
                                location="query",
                                name=field,
                                type_schema=get_schema(data),
                            ),
                        )
                    )
                    if not query_param.description:
                        query_param.description = (
                            f"{field} query parameter for {path} API"
                        )
                    if field in [
                        "tags",
                        "tags-any",
                        "not-tags",
                        "not-tags-any",
                    ]:
                        # Tags are special beasts
                        query_param.type_schema = TypeSchema(
                            type="array", items={"type": "string"}
                        )
                        query_param.style = "form"
                        query_param.explode = False
                    if field == "fixed_ips":
                        # TODO: Neutron is expecting a
                        # trick to get an array of
                        # objects. For now we only
                        # implement array of strings
                        # (whatever they are).
                        query_param.type_schema = TypeSchema(
                            type="array",
                            items={"type": "string"},
                            description="The IP addresses for the port. If the port has multiple IP addresses, this field has multiple entries. Each entry consists of IP address (ip_address) and the subnet ID from which the IP address is assigned (subnet_id).",
                        )
                        query_param.style = "form"
                        query_param.explode = False
                    if param_ref_name not in [
                        x.ref for x in operation_spec.parameters
                    ]:
                        operation_spec.parameters.append(
                            ParameterSchema(ref=param_ref_name)
                        )

        responses_spec = operation_spec.responses
        if method == "DELETE":
            response_code = "204"
        elif method == "POST":
            response_code = "201"
        else:
            response_code = "200"

        if path.endswith("/tags/{id}"):
            # /tags/{id} operation are non standard - they do not return body
            if method == "PUT":
                response_code = "201"
            elif method == "GET":
                response_code = "204"

        if response_code:
            rsp = responses_spec.setdefault(
                response_code, dict(description="Ok")
            )
            if response_code != "204" and method != "DELETE":
                # Arrange response placeholder
                schema_name = (
                    "".join([x.title() for x in path_resource_names])
                    + operation_name.title()
                    + "Response"
                )
                schema_ref = self._get_schema_ref(
                    openapi_spec,
                    schema_name,
                    description=f"Response of the {operation_spec.operationId} operation",
                    schema_def=attr_info,
                    method=method,
                    collection_key=collection,
                    resource_key=resource,
                    operation=operation_name,
                )

                if schema_ref:
                    rsp["content"] = {
                        "application/json": {"schema": {"$ref": schema_ref}}
                    }

    def _get_schema_ref(
        self,
        openapi_spec,
        name,
        description=None,
        schema_def=None,
        method=None,
        collection_key=None,
        resource_key=None,
        operation=None,
    ):
        schema = openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(
                type="object",
                description=LiteralScalarString(description),
            ),
        )

        # Here come schemas that are not present in Neutron
        if name == "ExtensionsIndexResponse":
            schema.properties = {
                "extensions": {
                    "type": "array",
                    "items": copy.deepcopy(neutron_schemas.EXTENSION_SCHEMA),
                }
            }
        elif name == "ExtensionShowResponse":
            schema.properties = {
                "extension": copy.deepcopy(neutron_schemas.EXTENSION_SCHEMA)
            }
        elif name.endswith("TagsIndexResponse"):
            schema.properties = {
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 255},
                }
            }
        elif name.endswith("TagsUpdate_AllResponse") or name.endswith(
            "TagsUpdate_AllRequest"
        ):
            schema.properties = {
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 255},
                }
            }
        elif name == "QuotasIndexResponse":
            schema.properties = {
                "quotas": {
                    "type": "array",
                    "items": copy.deepcopy(neutron_schemas.QUOTA_SCHEMA),
                }
            }
        elif name == "QuotasDetailsDetailsResponse":
            schema.properties = {
                "quota": copy.deepcopy(neutron_schemas.QUOTA_DETAILS_SCHEMA)
            }
        elif name in [
            "QuotaShowResponse",
            "QuotaUpdateRequest",
            "QuotaUpdateResponse",
            "QuotasDefaultDefaultResponse",
            "QuotasProjectProjectResponse",
        ]:
            schema.properties = {
                "quota": copy.deepcopy(neutron_schemas.QUOTA_SCHEMA)
            }
        elif name.endswith("TagUpdateRequest") or name.endswith(
            "TagUpdateResponse"
        ):
            # PUT tag does not have request body
            return None

        # ...
        elif name in [
            # Routers
            "RoutersAdd_Router_InterfaceAdd_Router_InterfaceRequest",
            "RoutersAdd_Router_InterfaceAdd_Router_InterfaceResponse",
            "RoutersRemove_Router_InterfaceRemove_Router_InterfaceRequest",
            "RoutersRemove_Router_InterfaceRemove_Router_InterfaceResponse",
            "RoutersAdd_ExtraroutesAdd_ExtraroutesRequest",
            "RoutersAdd_ExtraroutesAdd_ExtraroutesResponse",
            "RoutersRemove_ExtraroutesRemove_ExtraroutesRequest",
            "RoutersRemove_ExtraroutesRemove_ExtraroutesResponse",
            "RoutersAdd_External_GatewaysAdd_External_GatewaysRequest",
            "RoutersAdd_External_GatewaysAdd_External_GatewaysResponse",
            "RoutersUpdate_External_GatewaysUpdate_External_GatewaysRequest",
            "RoutersUpdate_External_GatewaysUpdate_External_GatewaysResponse",
            "RoutersRemove_External_GatewaysRemove_External_GatewaysRequest",
            "RoutersRemove_External_GatewaysRemove_External_GatewaysResponse",
            # L3 routers
            "RoutersL3_AgentsIndexResponse",
            "RoutersL3_AgentsCreateRequest",
            "RoutersL3_AgentsCreateResponse",
            "RoutersL3_AgentShowResponse",
            "RoutersL3_AgentUpdateRequest",
            "RoutersL3_AgentUpdateResponse"
            # Subnet pool
            "SubnetpoolsOnboard_Network_SubnetsOnboard_Network_SubnetsRequest",
            "SubnetpoolsOnboard_Network_SubnetsOnboard_Network_SubnetsResponse",
        ]:
            logging.warning("TODO: provide schema description for %s", name)

        # And now basic CRUD operations, those take whichever info is available in Controller._attr_info

        elif operation in ["index", "show", "create", "update", "delete"]:
            # Only CRUD operation are having request/response information avaiable
            send_props = {}
            return_props = {}
            # Consume request name to required fields mapping
            required_fields = neutron_schemas.REQUIRED_FIELDS_MAPPING.get(
                name, []
            )
            for field, data in schema_def.items():
                js_schema = get_schema(data)
                # Dirty hacks for corrupted schemas
                if field in ["availability_zones", "tags"]:
                    js_schema.update(
                        {"type": "array", "items": {"type": "string"}}
                    )
                elif field == "revision_number":
                    js_schema.update({"type": "integer"})
                elif field == "subnets":
                    js_schema.update(
                        {
                            "type": "array",
                            "items": {"type": "string", "format": "uuid"},
                        }
                    )
                elif field == "binding:vif_details":
                    js_schema.update({"type": "object"})
                if data.get(f"allow_{method.lower()}", False):
                    send_props[field] = js_schema
                if data.get("is_visible", False):
                    return_props[field] = js_schema
            if operation == "index" and collection_key:
                schema.properties = {
                    collection_key: {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": (
                                send_props
                                if name.endswith("Request")
                                else return_props
                            ),
                        },
                    }
                }
            else:
                if resource_key is not None:
                    schema.properties = {
                        resource_key: {
                            "type": "object",
                            "properties": (
                                send_props
                                if name.endswith("Request")
                                else return_props
                            ),
                        }
                    }
                    if required_fields:
                        schema.properties[resource_key]["required"] = list(
                            required_fields
                        )
        else:
            logging.warning("No Schema information for %s" % name)

        return f"#/components/schemas/{name}"


def get_schema(param_data):
    """Convert Neutron API definition into json schema"""
    schema: dict[str, Any] = {}
    validate = param_data.get("validate")
    convert_to = param_data.get("convert_to")
    typ_ = "string"
    if convert_to:
        if callable(convert_to):
            fname = convert_to.__name__
            if fname == "convert_to_boolean":
                typ_ = "boolean"
            elif fname == "convert_to_int":
                typ_ = "integer"

    if validate:
        if "type:uuid" in validate:
            schema = {"type": "string", "format": "uuid"}
        elif "type:uuid_or_none" in validate:
            schema = {"type": ["string", "null"], "format": "uuid"}
        elif "type:uuid_list" in validate:
            schema = {
                "type": "array",
                "items": {"type": "string", "format": "uuid"},
            }
        elif "type:string" in validate:
            length = validate.get("type:string")
            schema = {"type": "string"}
            if length:
                schema["maxLength"] = length
        elif "type:string_or_none" in validate:
            length = validate.get("type:string_or_none")
            schema = {"type": ["string", "null"]}
            if length:
                schema["maxLength"] = length
        elif "type:list_of_unique_strings" in validate:
            length = validate.get("type:list_of_unique_strings")
            schema = {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True,
            }
            if length:
                schema["items"]["maxLength"] = length
        elif "type:dict_or_none" in validate:
            schema = {"type": ["object", "null"]}
        elif "type:mac_address" in validate:
            schema = {"type": "string"}
        elif "type:dns_host_name" in validate:
            length = validate.get("type:dns_host_name")
            schema = {"type": "string", "format": "hostname"}
            if length:
                schema["maxLength"] = length
        elif "type:values" in validate:
            schema = {"type": typ_, "enum": list(validate["type:values"])}
        elif "type:range" in validate:
            r = validate["type:range"]
            schema = {"type": "number", "minimum": r[0], "maximum": r[1]}
        elif "type:range_or_none" in validate:
            r = validate["type:range_or_none"]
            schema = {
                "type": ["number", "null"],
                "minimum": r[0],
                "maximum": r[1],
            }
        elif "type:port_range" in validate:
            r = validate["type:port_range"]
            schema = {"type": "number", "minimum": r[0], "maximum": r[1]}
        elif "type:external_gw_info" in validate:
            schema = {
                "type": "object",
                "properties": {
                    "network_id": {"type": "string", "format": "uuid"},
                    "enable_snat": {"type": "boolean"},
                    "external_fixed_ips": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ip_address": {"type": "string"},
                                "subnet_id": {
                                    "type": "string",
                                    "format": "uuid",
                                },
                            },
                        },
                    },
                },
                "required": ["network_id"],
            }
        elif "type:availability_zone_hint_list" in validate:
            schema = {"type": "array", "items": {"type": "string"}}
        elif "type:hostroutes" in validate:
            schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "destination": {"type": "string"},
                        "nexthop": {"type": "string"},
                    },
                },
            }
        elif "type:network_segments" in validate:
            schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "provider:segmentation_id": {"type": "integer"},
                        "provider:physical_network": {"type": "string"},
                        "provider:network_type": {"type": "string"},
                    },
                },
            }
        elif "type:non_negative" in validate:
            schema = {"type": "integer", "minimum": 0}
        elif "type:dns_domain_name" in validate:
            length = validate.get("type:dns_domain_name")
            schema = {"type": "string", "format": "hostname"}
            if length:
                schema["maxLength"] = length
        elif "type:fixed_ips" in validate:
            schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ip_address": {
                            "type": "string",
                            "description": "IP Address",
                        },
                        "subnet_id": {
                            "type": "string",
                            "description": "The subnet ID from which the IP address is assigned",
                        },
                    },
                },
            }
        elif "type:allowed_address_pairs" in validate:
            schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ip_address": {"type": "string"},
                        "max_address": {"type": "string"},
                    },
                },
            }
        elif "type:list_of_any_key_specs_or_none" in validate:
            logging.warning(
                "TODO: Implement type:list_of_any_key_specs_or_none"
            )
            schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "extraProperties": True,
                },
                "x-openstack": {"todo": "implementme"},
            }
        elif "type:subnet_list" in validate:
            schema = {
                "type": "array",
                "items": {
                    "type": "string",
                    "format": "uuid",
                },
            }
        elif "type:service_plugin_type" in validate:
            schema = {
                "type": "string",
            }
        elif "type:ip_address" in validate:
            schema = {
                "type": "string",
            }
        elif "type:ip_address_or_none" in validate:
            schema = {
                "type": "string",
            }
        elif "type:subnet_or_none" in validate:
            schema = {"type": ["string", "null"]}
        elif "type:fip_dns_host_name" in validate:
            length = validate.get("type:fip_dns_host_name")
            schema = {"type": "string"}
            if length:
                schema["maxLength"] = length
        elif "type:name_not_default" in validate:
            length = validate.get("type:name_not_default")
            schema = {"type": "string"}
            if length:
                schema["maxLength"] = length
        elif "type:not_empty_string" in validate:
            length = validate.get("type:not_empty_string")
            schema = {"type": "string"}
            if length:
                schema["maxLength"] = length
        elif "type:subnetpool_id_or_none" in validate:
            schema = {"type": ["string", "null"]}
        elif "type:ip_pools" in validate:
            schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "string"},
                        "end": {"type": "string"},
                    },
                },
            }
        elif "type:nameservers" in validate:
            schema = {
                "type": "array",
                "items": {
                    "type": "string",
                },
            }
        elif "type:list_of_subnet_service_types" in validate:
            schema = {
                "type": "array",
                "description": "The service types associated with the subnet",
                "items": {
                    "type": "string",
                },
            }
        elif "type:dict_or_nodata" in validate:
            schema = get_schema(validate["type:dict_or_nodata"])
        elif "type:dict_or_empty" in validate:
            schema = get_schema(validate["type:dict_or_empty"])
        elif "type:list_of_subnets_or_none" in validate:
            schema = {"type": "array", "items": {"type": "string"}}
        else:
            raise RuntimeError(
                "Unsupported type %s in %s" % (validate, param_data)
            )
            schema = {"type": "string"}
    elif convert_to:
        # Nice way to get type of the field, isn't it?
        if convert_to.__name__ == "convert_to_boolean":
            schema = {"type": ["string", "boolean"]}
        elif convert_to.__name__ == "convert_to_boolean_if_not_none":
            schema = {"type": ["string", "boolean", "null"]}
        elif convert_to.__name__ == "convert_to_int":
            schema = {"type": ["string", "integer"]}
        elif convert_to.__name__ == "convert_to_int_if_not_none":
            schema = {"type": ["string", "integer", "null"]}
        else:
            logging.warning(
                "Unsupported conversion function %s used", convert_to.__name__
            )

    if not schema:
        default = param_data.get("default")
        if default is not None:
            if isinstance(default, list):
                schema = {"type": "array", "items": {"type": "string"}}
    if not schema:
        schema = {"type": "string"}

    return schema
