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
from multiprocessing import Process
from pathlib import Path

from jsonref import replace_refs
import routes
from ruamel.yaml.scalarstring import LiteralScalarString

from codegenerator.common.schema import (
    SpecSchema,
    TypeSchema,
    ParameterSchema,
    HeaderSchema,
)
from codegenerator.openapi.base import OpenStackServerSourceBase
from codegenerator.openapi.utils import merge_api_ref_doc

IMAGE_PARAMETERS = {
    "limit": {
        "in": "query",
        "name": "limit",
        "description": LiteralScalarString(
            "Requests a page size of items. Returns a number of items up to a limit value. Use the limit parameter to make an initial limited request and use the ID of the last-seen item from the response as the marker parameter value in a subsequent limited request."
        ),
        "schema": {"type": "integer"},
    },
    "marker": {
        "in": "query",
        "name": "marker",
        "description": LiteralScalarString(
            "The ID of the last-seen item. Use the limit parameter to make an initial limited request and use the ID of the last-seen item from the response as the marker parameter value in a subsequent limited request."
        ),
        "schema": {"type": "string"},
    },
    "id": {
        "in": "query",
        "name": "id",
        "description": "id filter parameter",
        "schema": {"type": "string"},
    },
    "name": {
        "in": "query",
        "name": "name",
        "description": LiteralScalarString(
            "Filters the response by a name, as a string. A valid value is the name of an image."
        ),
        "schema": {"type": "string"},
    },
    "visibility": {
        "in": "query",
        "name": "visibility",
        "description": LiteralScalarString(
            "Filters the response by an image visibility value. A valid value is public, private, community, shared, or all. (Note that if you filter on shared, the images included in the response will only be those where your member status is accepted unless you explicitly include a member_status filter in the request.) If you omit this parameter, the response shows public, private, and those shared images with a member status of accepted."
        ),
        "schema": {
            "type": "string",
            "enum": ["public", "private", "community", "shared", "all"],
        },
    },
    "member_status": {
        "in": "query",
        "name": "member_status",
        "description": LiteralScalarString(
            "Filters the response by a member status. A valid value is accepted, pending, rejected, or all. Default is accepted."
        ),
        "schema": {
            "type": "string",
            "enum": ["accepted", "pending", "rejected", "all"],
        },
    },
    "owner": {
        "in": "query",
        "name": "owner",
        "description": LiteralScalarString(
            "Filters the response by a project (also called a “tenant”) ID. Shows only images that are shared with you by the specified owner."
        ),
        "schema": {"type": "string"},
    },
    "status": {
        "in": "query",
        "name": "status",
        "description": LiteralScalarString(
            "Filters the response by an image status."
        ),
        "schema": {"type": "string"},
    },
    "size_min": {
        "in": "query",
        "name": "size_min",
        "description": LiteralScalarString(
            "Filters the response by a minimum image size, in bytes."
        ),
        "schema": {"type": "string"},
    },
    "size_max": {
        "in": "query",
        "name": "size_max",
        "description": LiteralScalarString(
            "Filters the response by a maximum image size, in bytes."
        ),
        "schema": {"type": "string"},
    },
    "protected": {
        "in": "query",
        "name": "protected",
        "description": LiteralScalarString(
            "Filters the response by the ‘protected’ image property. A valid value is one of ‘true’, ‘false’ (must be all lowercase). Any other value will result in a 400 response."
        ),
        "schema": {"type": "boolean"},
    },
    "os_hidden": {
        "in": "query",
        "name": "os_hidden",
        "description": LiteralScalarString(
            'When true, filters the response to display only "hidden" images. By default, "hidden" images are not included in the image-list response. (Since Image API v2.7)'
        ),
        "schema": {
            "type": "boolean",
        },
        "x-openstack": {"min-ver": "2.7"},
    },
    "sort_key": {
        "in": "query",
        "name": "sort_key",
        "description": LiteralScalarString(
            "Sorts the response by an attribute, such as name, id, or updated_at. Default is created_at. The API uses the natural sorting direction of the sort_key image attribute."
        ),
        "schema": {"type": "string"},
    },
    "sort_dir": {
        "in": "query",
        "name": "sort_dir",
        "description": LiteralScalarString(
            "Sorts the response by a set of one or more sort direction and attribute (sort_key) combinations. A valid value for the sort direction is asc (ascending) or desc (descending). If you omit the sort direction in a set, the default is desc."
        ),
        "schema": {"type": "string", "enum": ["asc", "desc"]},
    },
    "sort": {
        "in": "query",
        "name": "sort",
        "description": LiteralScalarString(
            "Sorts the response by one or more attribute and sort direction combinations. You can also set multiple sort keys and directions. Default direction is desc. Use the comma (,) character to separate multiple values. For example: `sort=name:asc,status:desc`"
        ),
        "schema": {"type": "string"},
    },
    "tag": {
        "in": "query",
        "name": "tag",
        "description": LiteralScalarString(
            "Filters the response by the specified tag value. May be repeated, but keep in mind that you're making a conjunctive query, so only images containing all the tags specified will appear in the response."
        ),
        "schema": {"type": "array", "items": {"type": "string"}},
        "style": "form",
        "explode": True,
    },
    "created_at": {
        "in": "query",
        "name": "created_at",
        "description": LiteralScalarString(
            "Specify a comparison filter based on the date and time when the resource was created."
        ),
        "schema": {"type": "string", "format": "date-time"},
    },
    "updated_at": {
        "in": "query",
        "name": "updated_at",
        "description": LiteralScalarString(
            "Specify a comparison filter based on the date and time when the resource was most recently modified."
        ),
        "schema": {"type": "string", "format": "date-time"},
    },
    "range": {
        "in": "header",
        "name": "Range",
        "description": LiteralScalarString(
            "The range of image data requested. Note that multi range requests are not supported."
        ),
        "schema": {"type": "string"},
    },
    "content-type": {
        "in": "header",
        "name": "Content-Type",
        "description": LiteralScalarString(
            "The media type descriptor of the body, namely application/octet-stream"
        ),
        "schema": {"type": "string"},
    },
    "x-image-meta-store": {
        "in": "header",
        "name": "X-Image-Meta-Store",
        "description": LiteralScalarString(
            "A store identifier to upload or import image data. Should only be included when making a request to a cloud that supports multiple backing stores. Use the Store Discovery call to determine an appropriate store identifier. Simply omit this header to use the default store."
        ),
        "schema": {"type": "string"},
    },
}

IMAGE_HEADERS = {
    "Content-Type": {
        "description": LiteralScalarString(
            "The media type descriptor of the body, namely application/octet-stream"
        ),
        "schema": {"type": "string"},
    },
    "Content-Length": {
        "description": LiteralScalarString(
            "The length of the body in octets (8-bit bytes)"
        ),
        "schema": {"type": "string"},
    },
    "Content-Md5": {
        "description": "The MD5 checksum of the body",
        "schema": {"type": "string"},
    },
    "Content-Range": {
        "description": "The content range of image data",
        "schema": {"type": "string"},
    },
    "OpenStack-image-store-ids": {
        "description": "list of available stores",
        "schema": {"type": "array", "items": {"type": "string"}},
    },
}


class GlanceGenerator(OpenStackServerSourceBase):
    URL_TAG_MAP = {
        "/versions": "version",
    }

    def __init__(self):
        self.api_version = "2.16"
        self.min_api_version = None

    def _api_ver_major(self, ver):
        return ver.ver_major

    def _api_ver_minor(self, ver):
        return ver.ver_minor

    def _api_ver(self, ver):
        return (ver.ver_major, ver.ver_minor)

    def generate(self, target_dir, args):
        proc = Process(target=self._generate, args=[target_dir, args])
        proc.start()
        proc.join()
        if proc.exitcode != 0:
            raise RuntimeError("Error generating Glance OpenAPI schma")
        return Path(target_dir, "openapi_specs", "image", "v2.yaml")

    def _generate(self, target_dir, args):
        from glance.api.v2 import router
        from glance.common import config
        from oslo_config import fixture as cfg_fixture

        self._config_fixture = self.useFixture(cfg_fixture.Config())

        config.parse_args(args=[])

        self.router = router.API(routes.Mapper())

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

        # Set global headers and parameters
        for name, definition in IMAGE_PARAMETERS.items():
            openapi_spec.components.parameters[name] = ParameterSchema(
                **definition
            )
        for name, definition in IMAGE_HEADERS.items():
            openapi_spec.components.headers[name] = HeaderSchema(**definition)

        for route in self.router.map.matchlist:
            if not route.conditions:
                continue
            self._process_route(route, openapi_spec, ver_prefix="/v2")

        self._sanitize_param_ver_info(openapi_spec, self.min_api_version)

        if args.api_ref_src:
            merge_api_ref_doc(openapi_spec, args.api_ref_src)

        self.dump_openapi(openapi_spec, impl_path, args.validate)

        return impl_path

    def _post_process_operation_hook(
        self, openapi_spec, operation_spec, path: str | None = None
    ):
        """Hook to allow service specific generator to modify details"""
        operationId = operation_spec.operationId

        if operationId == "images:get":
            for pname in [
                "limit",
                "marker",
                "name",
                "id",
                "owner",
                "protected",
                "status",
                "tag",
                "visibility",
                "os_hidden",
                "member_status",
                "size_max",
                "size_min",
                "created_at",
                "updated_at",
                "sort_dir",
                "sort_key",
                "sort",
            ]:
                ref = f"#/components/parameters/{pname}"
                if ref not in [x.ref for x in operation_spec.parameters]:
                    operation_spec.parameters.append(ParameterSchema(ref=ref))
        elif operationId == "images:post":
            key = "OpenStack-image-store-ids"
            ref = f"#/components/headers/{key}"
            operation_spec.responses["201"].setdefault("headers", {})
            operation_spec.responses["201"]["headers"].update(
                {key: {"$ref": ref}}
            )

        elif operationId == "images/image_id/file:put":
            for ref in [
                "#/components/parameters/content-type",
                "#/components/parameters/x-image-meta-store",
            ]:
                if ref not in [x.ref for x in operation_spec.parameters]:
                    operation_spec.parameters.append(ParameterSchema(ref=ref))
        elif operationId == "images/image_id/file:get":
            for ref in [
                "#/components/parameters/range",
            ]:
                if ref not in [x.ref for x in operation_spec.parameters]:
                    operation_spec.parameters.append(ParameterSchema(ref=ref))
            for code in ["200", "206"]:
                operation_spec.responses[code].setdefault("headers", {})
                for hdr in ["Content-Type", "Content-Md5", "Content-Length"]:
                    operation_spec.responses[code]["headers"].setdefault(
                        hdr,
                        {"$ref": f"#/components/headers/{hdr}"},
                    )
            operation_spec.responses["206"]["headers"].setdefault(
                "Content-Range",
                {"$ref": "#/components/headers/Content-Range"},
            )

    def _get_schema_ref(
        self,
        openapi_spec,
        name,
        description=None,
        schema_def=None,
        action_name=None,
    ):
        from glance.api.v2 import image_members
        from glance.api.v2 import images
        from glance.api.v2 import metadef_namespaces
        from glance.api.v2 import metadef_objects
        from glance.api.v2 import metadef_properties
        from glance.api.v2 import metadef_resource_types
        from glance.api.v2 import metadef_tags
        from glance.api.v2 import tasks
        from glance import schema as glance_schema

        ref: str
        mime_type: str = "application/json"

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
                name,
                TypeSchema(type="string", description="Schema data as string"),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ImagesTasksGet_Task_InfoResponse":
            openapi_spec.components.schemas.setdefault(
                name,
                self._get_glance_schema(
                    glance_schema.CollectionSchema(
                        "tasks", tasks.get_task_schema()
                    ),
                    name,
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
                name,
                self._get_glance_schema(images.get_collection_schema(), name),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ImagesMembersListResponse":
            openapi_spec.components.schemas.setdefault(
                name,
                self._get_glance_schema(
                    image_members.get_collection_schema(), name
                ),
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
                    metadef_namespaces.get_collection_schema(), name
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "MetadefsNamespacesObjectsListResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                self._get_glance_schema(
                    metadef_objects.get_collection_schema(), name
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "MetadefsNamespacesPropertiesListResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                self._get_glance_schema(
                    metadef_properties.get_collection_schema(), name
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "MetadefsResource_TypesListResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                self._get_glance_schema(
                    metadef_resource_types.get_collection_schema(), name
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "MetadefsNamespacesTagsListResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                self._get_glance_schema(
                    metadef_tags.get_collection_schema(), name
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ImageUpdateRequest":
            # openapi_spec.components.schemas.setdefault(
            #     name,
            #     self._get_glance_schema(
            #         metadef_tags.get_collection_schema(), name
            #     ),
            # )
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**{"type": "string", "format": "RFC 6902"}),
            )
            mime_type = "application/openstack-images-v2.1-json-patch"
            ref = f"#/components/schemas/{name}"
        elif name in [
            "ImagesFileUploadRequest",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**{"type": "string", "format": "binary"}),
            )
            ref = f"#/components/schemas/{name}"
            mime_type = "application/octet-stream"
        elif name in [
            "ImagesFileDownloadResponse",
        ]:
            openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**{"type": "string", "format": "binary"}),
            )
            ref = f"#/components/schemas/{name}"
            mime_type = "application/octet-stream"
        elif name in [
            "ImagesFileUploadResponse",
            "ImagesFileDownloadResponse",
        ]:
            return (None, None)
        elif schema_def:
            # Schema is known and is not an exception

            openapi_spec.components.schemas.setdefault(
                name, self._get_glance_schema(schema_def, name)
            )
            ref = f"#/components/schemas/{name}"

        else:
            (ref, mime_type) = super()._get_schema_ref(
                openapi_spec, name, description, schema_def=schema_def
            )
        return (ref, mime_type)

    def _get_glance_schema(self, schema, name: str | None = None):
        res = replace_refs(schema.raw(), proxies=False)
        res.pop("definitions", None)
        if "properties" in res and "type" not in res:
            res["type"] = "object"
        # List of image props that are by default integer, but in real life
        # are surely going i64 side
        i32_fixes = ["size", "virtual_size"]
        if name and name == "ImagesListResponse":
            for field in i32_fixes:
                res["properties"]["images"]["items"]["properties"][field][
                    "format"
                ] = "int64"
        if name and name == "ImageShowResponse":
            for field in i32_fixes:
                res["properties"][field]["format"] = "int64"
        return TypeSchema(**res)

    @classmethod
    def _get_response_codes(cls, method: str, operationId: str) -> list[str]:
        response_codes = super()._get_response_codes(method, operationId)
        if operationId == "images/image_id/file:put":
            response_codes = ["204"]
        if operationId == "images/image_id/file:get":
            response_codes = ["200", "204", "206"]
        return response_codes
