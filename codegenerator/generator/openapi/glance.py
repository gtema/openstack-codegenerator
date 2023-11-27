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
from pathlib import Path

import routes
from generator.common.schema import SpecSchema, TypeSchema
from generator.openapi.base import OpenStackServerSourceBase
from generator.openapi.utils import merge_api_ref_doc
from glance.api.v2 import image_members
from glance.api.v2 import images
from glance.api.v2 import metadef_namespaces
from glance.api.v2 import metadef_objects
from glance.api.v2 import metadef_properties
from glance.api.v2 import metadef_resource_types
from glance.api.v2 import metadef_tags
from glance.api.v2 import router
from glance.api.v2 import tasks
from glance.common import config
from glance import schema as glance_schema
from jsonref import replace_refs
from oslo_config import fixture as cfg_fixture
from ruamel.yaml.scalarstring import LiteralScalarString


class GlanceGenerator(OpenStackServerSourceBase):
    URL_TAG_MAP = {
        "/versions": "version",
    }

    def __init__(self):
        self.api_version = "2.16"
        self.min_api_version = None

        self._config_fixture = self.useFixture(cfg_fixture.Config())

        config.parse_args(args=[])

        self.router = router.API(routes.Mapper())

    def _api_ver_major(self, ver):
        return ver.ver_major

    def _api_ver_minor(self, ver):
        return ver.ver_minor

    def _api_ver(self, ver):
        return (ver.ver_major, ver.ver_minor)

    def generate(self, target_dir, args):
        work_dir = Path(target_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        impl_path = Path(work_dir, "openapi_specs", "image", "v2.yaml")
        impl_path.parent.mkdir(parents=True, exist_ok=True)

        openapi_spec = self.load_openapi(impl_path)
        if not openapi_spec:
            openapi_spec = SpecSchema(
                info=dict(
                    title="OpenStack Image API",
                    description=LiteralScalarString(
                        "Image API provided by Glance service"
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

        for route in self.router.map.matchlist:
            if not route.conditions:
                continue
            self._process_route(route, openapi_spec, ver_prefix="/v2")

        self._sanitize_param_ver_info(openapi_spec, self.min_api_version)

        if args.api_ref_src:
            merge_api_ref_doc(openapi_spec, args.api_ref_src)

        self.dump_openapi(openapi_spec, impl_path, args.validate)

        return impl_path

    def _get_schema_ref(
        self,
        openapi_spec,
        name,
        description=None,
        schema_def=None,
        action_name=None,
    ):
        if name == "TasksListResponse":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **{
                        "name": "tasks",
                        "type": "object",
                        "properties": {
                            "schema": {"type": "string"},
                            "tasks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": copy.deepcopy(
                                        schema_def.properties
                                    ),
                                },
                            },
                        },
                    }
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name.startswith("Schemas") and name.endswith("Response"):
            openapi_spec.components.schemas.setdefault(
                name, TypeSchema(type="string")
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ImagesTasksGet_Task_InfoResponse":
            openapi_spec.components.schemas.setdefault(
                name,
                self._get_glance_schema(
                    glance_schema.CollectionSchema(
                        "tasks", tasks.get_task_schema()
                    )
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ImagesImportImport_ImageRequest":
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **{
                        "type": "object",
                        "properties": {
                            "method": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "uri": {"type": "string"},
                                    "glance_image_id": {"type": "string"},
                                    "glance_region": {"type": "string"},
                                    "glance_service_interface": {
                                        "type": "string"
                                    },
                                },
                            },
                            "stores": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "all_stores": {"type": "boolean"},
                            "all_stores_must_success": {"type": "boolean"},
                        },
                    }
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ImagesImportImport_ImageResponse":
            openapi_spec.components.schemas.setdefault(name, TypeSchema())
            ref = f"#/components/schemas/{name}"
        elif name == "ImagesListResponse":
            openapi_spec.components.schemas.setdefault(
                name, self._get_glance_schema(images.get_collection_schema())
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ImagesMembersListResponse":
            openapi_spec.components.schemas.setdefault(
                name,
                self._get_glance_schema(image_members.get_collection_schema()),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "InfoImportGet_Image_ImportResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **{
                        "type": "object",
                        "properties": {
                            "import-methods": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "type": {"type": "string"},
                                    "value": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                            }
                        },
                    }
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "InfoStoresGet_StoresResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **{
                        "type": "object",
                        "properties": {
                            "stores": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "description": {"type": "string"},
                                        "default": {"type": "boolean"},
                                    },
                                },
                            }
                        },
                    }
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "InfoStoresDetailGet_Stores_DetailResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **{
                        "type": "object",
                        "properties": {
                            "stores": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "description": {"type": "string"},
                                        "default": {"type": "boolean"},
                                        "type": {"type": "string"},
                                        "weight": {"type": "number"},
                                        "properties": {
                                            "type": "object",
                                            "additionalProperties": True,
                                        },
                                    },
                                },
                            }
                        },
                    }
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "MetadefsNamespacesListResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                self._get_glance_schema(
                    metadef_namespaces.get_collection_schema()
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "MetadefsNamespacesObjectsListResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                self._get_glance_schema(
                    metadef_objects.get_collection_schema()
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "MetadefsNamespacesPropertiesListResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                self._get_glance_schema(
                    metadef_properties.get_collection_schema()
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "MetadefsResource_TypesListResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                self._get_glance_schema(
                    metadef_resource_types.get_collection_schema()
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "MetadefsNamespacesTagsListResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                self._get_glance_schema(metadef_tags.get_collection_schema()),
            )
            ref = f"#/components/schemas/{name}"
        elif schema_def:
            # Schema is known and is not an exception

            openapi_spec.components.schemas.setdefault(
                name, self._get_glance_schema(schema_def)
            )
            ref = f"#/components/schemas/{name}"

        else:
            ref = super()._get_schema_ref(
                openapi_spec, name, description, schema_def=schema_def
            )
        return ref

    def _get_glance_schema(self, schema):
        res = replace_refs(schema.raw(), proxies=False)
        res.pop("definitions", None)
        return TypeSchema(**res)
