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
from pathlib import Path
from unittest import mock

import fixtures

from codegenerator.common.schema import SpecSchema
from codegenerator.openapi.base import OpenStackServerSourceBase
from codegenerator.openapi.utils import merge_api_ref_doc

from ruamel.yaml.scalarstring import LiteralScalarString


class OctaviaGenerator(OpenStackServerSourceBase):
    URL_TAG_MAP = {
        "/lbaas/listeners": "listeners",
        "/lbaas/loadbalancers": "load-balancers",
        "/lbaas/pools/{pool_id}/members": "members",
        "/lbaas/pools": "pools",
        "/lbaas/healthmonitors": "healthmonitors",
        "/lbaas/l7policies/{l7policy_id}/rules": "l7-rules",
        "/lbaas/l7policies": "l7-policies",
        "/lbaas/quotas": "quotas",
        "/lbaas/providers": "providers",
        "/lbaas/flavorprofiles": "flavor-profiles",
        "/lbaas/flavors": "flavors",
        "/lbaas/availabilityzoneprofiles": "avaiability-zone-profiles",
        "/lbaas/availabilityzones": "avaiability-zones",
        "/lbaas/amphorae": "amphorae",
        "/octavia/amphorae": "amphorae",
    }

    def __init__(self):
        self.api_version = "2.27"
        self.min_api_version = "2.0"

    def _fake_create_transport(self, url):
        import oslo_messaging as messaging
        from oslo_config import cfg

        if url not in self._buses:
            self._buses[url] = messaging.get_rpc_transport(cfg.CONF, url=url)
        return self._buses[url]

    def _api_ver_major(self, ver):
        return ver.ver_major

    def _api_ver_minor(self, ver):
        return ver.ver_minor

    def _api_ver(self, ver):
        return (ver.ver_major, ver.ver_minor)

    def _build_routes(self, mapper, node, path=""):
        for part in [x for x in dir(node) if callable(getattr(node, x))]:
            # Iterate over functions to find what is exposed on the current
            # level
            obj = getattr(node, part)
            _pecan = getattr(obj, "_pecan", None)
            exposed = getattr(obj, "exposed", None)
            if _pecan and exposed:
                # Only whatever is pecan exposed is of interest
                conditions = {}
                action = None
                url = path
                resource = None
                parent = url.split("/")[-1]
                # Construct resource name from the path
                if parent.endswith("ies"):
                    resource = parent[0 : len(parent) - 3] + "y"
                else:
                    resource = parent[0:-1]
                if path.startswith("/v2/lbaas/quotas"):
                    # Hack path parameter name for quotas
                    resource = "project"
                # Identify the action from function name
                # https://pecan.readthedocs.io/en/latest/rest.html#url-mapping
                if part == "get_one":
                    conditions["method"] = ["GET"]
                    action = "show"
                    url += f"/{{{resource}_id}}"
                elif part == "get_all":
                    conditions["method"] = ["GET"]
                    action = "list"
                elif part == "get":
                    conditions["method"] = ["GET"]
                    action = "get"
                    # "Get" is tricky, it can be normal and root, so need to inspect params
                    sig = inspect.signature(obj)
                    for pname, pval in sig.parameters.items():
                        if "id" in pname and pval.default == pval.empty:
                            url += f"/{{{resource}_id}}"
                elif part == "post":
                    conditions["method"] = ["POST"]
                    action = "create"
                    # url += f"/{{{resource}_id}}"
                elif part == "put":
                    conditions["method"] = ["PUT"]
                    action = "update"
                    url += f"/{{{resource}_id}}"
                elif part == "delete":
                    conditions["method"] = ["DELETE"]
                    action = "delete"
                    url += f"/{{{resource}_id}}"

                if action:
                    # If we identified method as "interesting" register it into
                    # the routes mapper
                    mapper.connect(
                        None,
                        url,
                        controller=obj,
                        action=action,
                        conditions=conditions,
                    )
                # yield part
        if not hasattr(node, "__dict__"):
            return
        for subcontroller, v in node.__dict__.items():
            # Iterate over node attributes for subcontrollers
            if subcontroller in [
                "repositories",
                "cert_manager",
                "__wrapped__",
            ]:
                # Not underested in those
                continue
            subpath = f"{path}/{subcontroller}"
            self._build_routes(mapper, v, subpath)

        return

    def generate(self, target_dir, args):
        proc = Process(target=self._generate, args=[target_dir, args])
        proc.start()
        proc.join()
        if proc.exitcode != 0:
            raise RuntimeError("Error generating Octavia OpenAPI schma")
        return Path(target_dir, "openapi_specs", "load-balancing", "v2.yaml")

    def _generate(self, target_dir, args):
        from octavia.api import root_controller
        from octavia.common import config, rpc
        from octavia.api.v2.controllers import amphora
        from octavia.api.v2.controllers import l7rule
        from octavia.api.v2.controllers import listener
        from octavia.api.v2.controllers import load_balancer
        from octavia.api.v2.controllers import member
        from octavia.api.v2.controllers import provider
        from oslo_config import cfg

        # import oslo_messaging as messaging
        from oslo_messaging import conffixture as messaging_conffixture
        from pecan import make_app as pecan_make_app
        from routes import Mapper

        work_dir = Path(target_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        impl_path = Path(
            work_dir, "openapi_specs", "load-balancing", "v2.yaml"
        )
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        openapi_spec = self.load_openapi(Path(impl_path))
        if not openapi_spec:
            openapi_spec = SpecSchema(
                info=dict(
                    title="OpenStack Load Balancing API",
                    description=LiteralScalarString(
                        "Load Balancing API provided by Octavia service"
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
                ),
            )
        config.register_cli_opts()

        self._buses = {}

        self.messaging_conf = messaging_conffixture.ConfFixture(cfg.CONF)
        self.messaging_conf.transport_url = "fake:/"
        self.useFixture(self.messaging_conf)
        self.useFixture(
            fixtures.MonkeyPatch(
                "octavia.common.rpc.create_transport",
                self._fake_create_transport,
            )
        )
        with mock.patch("octavia.common.rpc.get_transport_url") as mock_gtu:
            mock_gtu.return_value = None
            rpc.init()

        self.app = pecan_make_app(root_controller.RootController())
        self.root = self.app.application.root

        mapper = Mapper()

        self._build_routes(mapper, self.root)
        # Additional amphora routes
        mapper.connect(
            None,
            "/v2/octavia/amphorae/{amphora_id}/stats",
            controller=amphora.AmphoraStatsController.get,
            action="stats",
            conditions={"method": ["GET"]},
        )
        mapper.connect(
            None,
            "/v2/octavia/amphorae/{amphora_id}/config",
            controller=amphora.AmphoraUpdateController.put,
            action="config",
            conditions={"method": ["PUT"]},
        )
        mapper.connect(
            None,
            "/v2/octavia/amphorae/{amphora_id}/failover",
            controller=amphora.FailoverController.put,
            action="failover",
            conditions={"method": ["PUT"]},
        )
        # Additional AZ routes
        mapper.connect(
            None,
            "/v2/lbaas/providers/{provider}/flavor_capabilities",
            controller=provider.FlavorCapabilitiesController.get_all,
            action="flavor_capabilities",
            conditions={"method": ["GET"]},
        )
        mapper.connect(
            None,
            "/v2/lbaas/providers/{provider}/availability_zone_capabilities",
            controller=provider.AvailabilityZoneCapabilitiesController.get_all,
            action="az_capabilities",
            conditions={"method": ["GET"]},
        )
        # L7Rules routes
        mapper.connect(
            None,
            "/v2/lbaas/l7policies/{l7policy_id}/rules",
            controller=l7rule.L7RuleController.get_all,
            action="index",
            conditions={"method": ["GET"]},
        )
        mapper.connect(
            None,
            "/v2/lbaas/l7policies/{l7policy_id}/rules",
            controller=l7rule.L7RuleController.post,
            action="create",
            conditions={"method": ["POST"]},
        )
        mapper.connect(
            None,
            "/v2/lbaas/l7policies/{l7policy_id}/rules/{rule_id}",
            controller=l7rule.L7RuleController.get,
            action="create",
            conditions={"method": ["GET"]},
        )
        mapper.connect(
            None,
            "/v2/lbaas/l7policies/{l7policy_id}/rules/{rule_id}",
            controller=l7rule.L7RuleController.put,
            action="update",
            conditions={"method": ["PUT"]},
        )
        mapper.connect(
            None,
            "/v2/lbaas/l7policies/{l7policy_id}/rules/{rule_id}",
            controller=l7rule.L7RuleController.delete,
            action="delete",
            conditions={"method": ["DELETE"]},
        )
        # Pool Member routes
        mapper.connect(
            None,
            "/v2/lbaas/pools/{pool_id}/members",
            controller=member.MemberController.get_all,
            action="index",
            conditions={"method": ["GET"]},
        )
        mapper.connect(
            None,
            "/v2/lbaas/pools/{pool_id}/members",
            controller=member.MemberController.post,
            action="create",
            conditions={"method": ["POST"]},
        )
        mapper.connect(
            None,
            "/v2/lbaas/pools/{pool_id}/members",
            controller=member.MembersController.put,
            action="create",
            conditions={"method": ["PUT"]},
        )
        mapper.connect(
            None,
            "/v2/lbaas/pools/{pool_id}/members/{member_id}",
            controller=member.MemberController.get,
            action="create",
            conditions={"method": ["GET"]},
        )
        mapper.connect(
            None,
            "/v2/lbaas/pools/{pool_id}/members/{member_id}",
            controller=member.MemberController.put,
            action="update",
            conditions={"method": ["PUT"]},
        )
        mapper.connect(
            None,
            "/v2/lbaas/pools/{pool_id}/members/{member_id}",
            controller=member.MemberController.delete,
            action="delete",
            conditions={"method": ["DELETE"]},
        )
        # Listener stat
        mapper.connect(
            None,
            "/v2/lbaas/listeners/{listener_id}/stats",
            controller=listener.StatisticsController.get,
            action="stats",
            conditions={"method": ["GET"]},
        )
        # Loadbalancer OPs stat
        mapper.connect(
            None,
            "/v2/lbaas/loadbalancers/{loadbalancer_id}/stats",
            controller=load_balancer.StatisticsController.get,
            action="stats",
            conditions={"method": ["GET"]},
        )
        mapper.connect(
            None,
            "/v2/lbaas/loadbalancers/{loadbalancer_id}/status",
            controller=load_balancer.StatusController.get,
            action="status",
            conditions={"method": ["GET"]},
        )
        mapper.connect(
            None,
            "/v2/lbaas/loadbalancers/{loadbalancer_id}/statuses",
            controller=load_balancer.StatusController.get,
            action="status",
            conditions={"method": ["GET"]},
        )
        mapper.connect(
            None,
            "/v2/lbaas/loadbalancers/{loadbalancer_id}/failover",
            controller=load_balancer.FailoverController.put,
            action="failover",
            conditions={"method": ["PUT"]},
        )

        for route in mapper.matchlist:
            # Only generate docs for "/v2/lbaas" and "/v2/octavia"
            if not (
                route.routepath.startswith("/v2/lbaas")
                or route.routepath.startswith("/v2/octavia")
            ):
                continue
            self._process_route(route, openapi_spec, framework="pecan")

        if args.api_ref_src:
            merge_api_ref_doc(
                openapi_spec, args.api_ref_src, allow_strip_version=False
            )

        self.dump_openapi(openapi_spec, Path(impl_path), args.validate)

        return impl_path
