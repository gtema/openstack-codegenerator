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
from multiprocessing import Process
from pathlib import Path

from ruamel.yaml.scalarstring import LiteralScalarString

from codegenerator.common.schema import (
    SpecSchema,
)
from codegenerator.openapi.base import OpenStackServerSourceBase
from codegenerator.openapi.utils import merge_api_ref_doc


class PlacementGenerator(OpenStackServerSourceBase):
    URL_TAG_MAP = {
        "/versions": "version",
    }

    def _api_ver_major(self, ver):
        return ver.ver_major

    def _api_ver_minor(self, ver):
        return ver.ver_minor

    def _api_ver(self, ver):
        return (ver.ver_major, ver.ver_minor)

    def _generate(self, target_dir, args):
        from oslo_config import cfg
        from oslo_config import fixture as config_fixture

        from placement import microversion
        from placement import handler
        from placement import conf

        self.api_version = microversion.max_version_string()
        self.min_api_version = microversion.min_version_string()

        config = cfg.ConfigOpts()
        conf_fixture = self.useFixture(config_fixture.Config(config))
        conf.register_opts(conf_fixture.conf)
        handler = handler.PlacementHandler(config=conf_fixture.conf)

        self.router = handler._map

        work_dir = Path(target_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        impl_path = Path(
            work_dir, "openapi_specs", "placement", f"v{self.api_version}.yaml"
        )
        impl_path.parent.mkdir(parents=True, exist_ok=True)

        openapi_spec = self.load_openapi(impl_path)
        if not openapi_spec:
            openapi_spec = SpecSchema(
                info=dict(
                    title="OpenStack Placement API",
                    description=LiteralScalarString(
                        "Placement API provided by Placement service"
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

        for route in self.router.matchlist:
            self._process_route(route, openapi_spec)

        self._sanitize_param_ver_info(openapi_spec, self.min_api_version)

        if args.api_ref_src:
            merge_api_ref_doc(
                openapi_spec,
                args.api_ref_src,
                allow_strip_version=False,
            )

        self.dump_openapi(openapi_spec, impl_path, args.validate)

        lnk = Path(impl_path.parent, "v1.yaml")
        lnk.unlink(missing_ok=True)
        lnk.symlink_to(impl_path.name)

        return impl_path

    def generate(self, target_dir, args):
        proc = Process(target=self._generate, args=[target_dir, args])
        proc.start()
        proc.join()
        if proc.exitcode != 0:
            raise RuntimeError("Error generating Placement OpenAPI schema")
