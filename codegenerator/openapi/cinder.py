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

from codegenerator.common.schema import ParameterSchema
from codegenerator.common.schema import SpecSchema
from codegenerator.common.schema import TypeSchema
from codegenerator.openapi.base import OpenStackServerSourceBase
from codegenerator.openapi import cinder_schemas
from codegenerator.openapi.utils import merge_api_ref_doc


class CinderV3Generator(OpenStackServerSourceBase):
    URL_TAG_MAP = {
        "/versions": "version",
    }

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
            raise RuntimeError("Error generating Cinder OpenAPI schma")
        return Path(target_dir, "openapi_specs", "block-storage", "v3.yaml")

    def _generate(self, target_dir, args, *pargs, **kwargs):
        from cinder import objects, rpc
        from cinder.api.openstack import api_version_request
        from cinder.common import config
        from cinder.tests.unit.test import Database as db_fixture

        # Register all Cinder objects
        objects.register_all()

        CONF = config.CONF

        self.api_version = api_version_request._MAX_API_VERSION
        self.min_api_version = api_version_request._MIN_API_VERSION

        rpc.init(CONF)

        CONF.set_default("connection", "sqlite:///", "database")
        CONF.set_default("sqlite_synchronous", False, "database")

        self.useFixture(db_fixture())

        from cinder.api.v3 import router

        self.router = router.APIRouter()

        work_dir = Path(target_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        impl_path = Path(work_dir, "openapi_specs", "block-storage", "v3.yaml")
        impl_path.parent.mkdir(parents=True, exist_ok=True)

        openapi_spec = self.load_openapi(impl_path)
        if not openapi_spec:
            openapi_spec = SpecSchema(
                info=dict(
                    title="OpenStack Volume API",
                    description=LiteralScalarString(
                        "Volume API provided by Cinder service"
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

        # Set global parameters
        for name, definition in cinder_schemas.VOLUME_PARAMETERS.items():
            openapi_spec.components.parameters[name] = ParameterSchema(
                **definition
            )

        for route in self.router.map.matchlist:
            # if route.routepath.startswith("/{project"):
            #    continue
            if route.routepath.endswith(".:(format)"):
                continue

            self._process_route(route, openapi_spec, ver_prefix="/v3")

        self._sanitize_param_ver_info(openapi_spec, self.min_api_version)

        if args.api_ref_src:
            merge_api_ref_doc(openapi_spec, args.api_ref_src)

        self.dump_openapi(openapi_spec, impl_path, args.validate)

        return impl_path

    def _post_process_operation_hook(self, openapi_spec, operation_spec):
        """Hook to allow service specific generator to modify details"""
        operationId = operation_spec.operationId

        if operationId in [
            "project_id/volumes:get",
            "volumes:get",
            "project_id/volumes/detail:get",
            "volumes/detail:get",
        ]:
            for pname in [
                "all_tenants",
                "sort",
                "sort_key",
                "sort_dir",
                "limit",
                "offset",
                "marker",
                "with_count",
                "created_at",
                "updated_at",
                "consumes_quota",
            ]:
                ref = f"#/components/parameters/{pname}"
                if ref not in [x.ref for x in operation_spec.parameters]:
                    operation_spec.parameters.append(ParameterSchema(ref=ref))
        elif operationId in [
            "project_id/volumes/summary:get",
        ]:
            for pname in [
                "all_tenants",
            ]:
                ref = f"#/components/parameters/{pname}"
                if ref not in [x.ref for x in operation_spec.parameters]:
                    operation_spec.parameters.append(ParameterSchema(ref=ref))

    def _get_schema_ref(
        self,
        openapi_spec,
        name,
        description=None,
        schema_def=None,
        action_name=None,
    ):
        mime_type: str = "application/json"
        if name == "VolumesListResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**cinder_schemas.VOLUMES_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        if name == "VolumesDetailResponse":
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**cinder_schemas.VOLUMES_DETAIL_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "VolumeShowResponse",
            "VolumeUpdateResponse",
            "VolumesCreateResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**cinder_schemas.VOLUME_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        else:
            (ref, mime_type) = super()._get_schema_ref(
                openapi_spec, name, description, action_name=action_name
            )
        return (ref, mime_type)
