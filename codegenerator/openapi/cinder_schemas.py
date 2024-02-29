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

from cinder.api.schemas import admin_actions
from cinder.api.validation import parameter_types

# NOTE(gtema): This is a temporary location for schemas not currently defined
# in Glance. Once everything is stabilized those must be moved directly to Glabne

LINK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Links to the resources in question. See [API Guide / Links and References](https://docs.openstack.org/api-guide/compute/links_and_references.html) for more info.",
    "properties": {
        "href": {"type": "string", "format": "uri"},
        "rel": {"type": "string"},
    },
}

LINKS_SCHEMA: dict[str, Any] = {
    "type": "array",
    "description": "Links to the resources in question. See [API Guide / Links and References](https://docs.openstack.org/api-guide/compute/links_and_references.html) for more info.",
    "items": copy.deepcopy(LINK_SCHEMA),
}

ATTACHMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "server_id": {"type": "string", "format": "uuid"},
        "attachment_id": {"type": "string", "format": "uuid"},
        "attached_at": {"type": "string", "format": "date-time"},
        "host_name": {"type": "string"},
        "volume_id": {"type": "string", "format": "uuid"},
        "device": {"type": "string"},
        "id": {"type": "string", "format": "uuid"},
    },
}

ATTACHMENTS_SCHEMA = {
    "type": "array",
    "items": copy.deepcopy(ATTACHMENT_SCHEMA),
}

METADATA_SCHEMA = {
    "type": "object",
    "patternProperties": {
        "^[a-zA-Z0-9-_:. /]{1,255}$": {"type": "string", "maxLength": 255},
    },
    "additionalProperties": False,
    "description": "A metadata object. Contains one or more metadata key and value pairs that are associated with the resource.",
}

METADATA_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Metadata key and value pairs. The maximum size for each metadata key and value pair is 255 bytes.",
    "properties": {"metadata": METADATA_SCHEMA},
}

METADATA_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Metadata key and value pairs. The maximum size for each metadata key and value pair is 255 bytes.",
    "properties": {"meta": {"maxProperties": 1, **METADATA_SCHEMA}},
}

VOLUME_SHORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "A volume object.",
    "properties": {
        "name": {
            "type": ["string", "null"],
            "description": "The volume name.",
        },
        "links": {
            "description": "The volume links.",
            **copy.deepcopy(LINKS_SCHEMA),
        },
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the volume.",
        },
    },
}

VOLUME_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "A volume object.",
    "properties": {
        "name": {
            "type": ["string", "null"],
            "description": "The volume name.",
        },
        "description": {
            "type": ["string", "null"],
            "description": "The volume description.",
        },
        "volume_type": {
            "type": "string",
            "description": "The associated volume type name for the volume.",
        },
        "metadata": copy.deepcopy(METADATA_SCHEMA),
        "snapshot_id": {
            "type": "string",
            "format": "uuid",
            "description": "To create a volume from an existing snapshot, specify the UUID of the volume snapshot. The volume is created in same availability zone and with same size as the snapshot.",
        },
        "source_volid": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the source volume. The API creates a new volume with the same size as the source volume unless a larger size is requested.",
        },
        "consistencygroup_id": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the consistency group.",
        },
        "size": {
            "type": "integer",
            "format": "int64",
            "description": "The size of the volume, in gibibytes (GiB).",
        },
        "availability_zone": {
            "type": "string",
            "description": "The name of the availability zone.",
        },
        "multiattach": {
            "type": "boolean",
            "description": "If true, this volume can attach to more than one instance.",
        },
        "status": {
            "type": "string",
            "description": "The volume status.",
        },
        "migration_status": {
            "type": "string",
            "description": "The volume migration status. Admin only.",
        },
        "attachments": {
            "description": "Instance attachment information. If this volume is attached to a server instance, the attachments list includes the UUID of the attached server, an attachment UUID, the name of the attached host, if any, the volume UUID, the device, and the device UUID. Otherwise, this list is empty.",
            **copy.deepcopy(ATTACHMENTS_SCHEMA),
        },
        "links": {
            "description": "The volume links.",
            **copy.deepcopy(LINKS_SCHEMA),
        },
        "encrypted": {
            "type": "boolean",
            "description": "If true, this volume is encrypted.",
        },
        "created_at": {
            "type": "string",
            "format": "date-time",
            "description": "The date and time when the resource was created.",
        },
        "updated_at": {
            "type": "string",
            "format": "date-time",
            "description": "The date and time when the resource was updated.",
        },
        "replication_status": {
            "type": "string",
            "description": "The volume replication status.",
        },
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the volume.",
        },
        "user_id": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the user.",
        },
        "volume_type_id": {
            "type": "string",
            "format": "uuid",
            "description": "The associated volume type ID for the volume.",
            "x-openstack": {"min-ver": "3.63"},
        },
        "group_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the group.",
            "x-openstack": {"min-ver": "3.63"},
        },
        "provider_id": {
            "type": ["string", "null"],
            "format": "uuid",
            "description": "The provider ID for the volume. The value is either a string set by the driver or null if the driver doesn’t use the field or if it hasn’t created it yet. Only returned for administrators.",
            "x-openstack": {"min-ver": "3.21"},
        },
        "service_uuid": {
            "type": "string",
            "format": "uuid",
            "description": "A unique identifier that’s used to indicate what node the volume-service for a particular volume is being serviced by.",
            "x-openstack": {"min-ver": "3.48"},
        },
        "shared_targets": {
            "type": "boolean",
            "description": "An indicator whether the host connecting the volume should lock for the whole attach/detach process or not. true means only is iSCSI initiator running on host doesn’t support manual scans, false means never use locks, and null means to always use locks. Look at os-brick’s guard_connection context manager. Default=True.",
            "x-openstack": {"min-ver": "3.48"},
        },
        "cluster_name": {
            "type": "string",
            "description": "The cluster name of volume backend.",
            "x-openstack": {"min-ver": "3.61"},
        },
        "consumes_quota": {
            "type": "boolean",
            "description": "Whether this resource consumes quota or not. Resources that not counted for quota usage are usually temporary internal resources created to perform an operation.",
            "x-openstack": {"min-ver": "3.65"},
        },
    },
    "additionalProperties": True,
}

VOLUME_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "A volume object.",
    "properties": {"volume": copy.deepcopy(VOLUME_SCHEMA)},
    "required": ["volume"],
    "additionalProperties": False,
}

VOLUMES_SCHEMA = {
    "type": "object",
    "description": "A container with list of volume objects.",
    "properties": {
        "volumes": {
            "type": "array",
            "items": copy.deepcopy(VOLUME_SHORT_SCHEMA),
            "description": "A list of volume objects.",
        },
    },
}

VOLUMES_DETAIL_SCHEMA = {
    "type": "object",
    "description": "A container with list of volume objects.",
    "properties": {
        "volumes": {
            "type": "array",
            "items": copy.deepcopy(VOLUME_SCHEMA),
            "description": "A list of volume objects.",
        },
    },
}

VOLUME_PARAMETERS = {
    "all_tenants": {
        "in": "query",
        "name": "all_tenans",
        "schema": {
            "type": "boolean",
        },
        "description": "Shows details for all project. Admin only.",
    },
    "sort": {
        "in": "query",
        "name": "sort",
        "schema": {
            "type": "string",
        },
        "description": "Comma-separated list of sort keys and optional sort directions in the form of < key > [: < direction > ]. A valid direction is asc (ascending) or desc (descending).",
    },
    "sort_key": {
        "in": "query",
        "name": "sort_key",
        "schema": {
            "type": "string",
        },
        "description": "Sorts by an attribute. A valid value is name, status, container_format, disk_format, size, id, created_at, or updated_at. Default is created_at. The API uses the natural sorting direction of the sort_key attribute value. Deprecated in favour of the combined sort parameter.",
    },
    "sort_dir": {
        "in": "query",
        "name": "sort_dir",
        "schema": {
            "type": "string",
            "enum": ["asc", "desc"],
        },
        "description": "Sorts by one or more sets of attribute and sort direction combinations. If you omit the sort direction in a set, default is desc. Deprecated in favour of the combined sort parameter.",
    },
    "limit": {
        "in": "query",
        "name": "limit",
        "schema": {
            "type": "integer",
        },
        "description": "Requests a page size of items. Returns a number of items up to a limit value. Use the limit parameter to make an initial limited request and use the ID of the last-seen item from the response as the marker parameter value in a subsequent limited request.",
    },
    "offset": {
        "in": "query",
        "name": "offset",
        "schema": {
            "type": "integer",
        },
        "description": "Used in conjunction with limit to return a slice of items. offset is where to start in the list.",
    },
    "marker": {
        "in": "query",
        "name": "marker",
        "schema": {
            "type": "string",
            "format": "uuid",
        },
        "description": "The ID of the last-seen item. Use the limit parameter to make an initial limited request and use the ID of the last-seen item from the response as the marker parameter value in a subsequent limited request.",
    },
    "with_count": {
        "in": "query",
        "name": "with_count",
        "schema": {
            "type": "boolean",
        },
        "description": "Whether to show count in API response or not, default is False.",
        "x-openstack": {"min-ver": "3.45"},
    },
    "created_at": {
        "in": "query",
        "name": "created_at",
        "schema": {
            "type": "string",
            "format": "date-time",
        },
        "description": "Filters reuslts by a time that resources are created at with time comparison operators: gt/gte/eq/neq/lt/lte.",
        "x-openstack": {"min-ver": "3.60"},
    },
    "updated_at": {
        "in": "query",
        "name": "updated_at",
        "schema": {
            "type": "string",
            "format": "date-time",
        },
        "description": "Filters reuslts by a time that resources are updated at with time comparison operators: gt/gte/eq/neq/lt/lte.",
        "x-openstack": {"min-ver": "3.60"},
    },
    "consumes_quota": {
        "in": "query",
        "name": "consumes_quota",
        "schema": {
            "type": "boolean",
        },
        "description": "Filters results by consumes_quota field. Resources that don’t use quotas are usually temporary internal resources created to perform an operation. Default is to not filter by it. Filtering by this option may not be always possible in a cloud, see List Resource Filters to determine whether this filter is available in your cloud.",
        "x-openstack": {"min-ver": "3.65"},
    },
}

VOLUME_RESET_STATUS_SCHEMA: dict[str, Any] = admin_actions.reset

VOLUME_UPLOAD_IMAGE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "container_format": {
            "type": "string",
            "description": "Container format for the new image. Default is bare.",
        },
        "disk_format": {
            "type": "string",
            "description": "Disk format for the new image. Default is raw.",
        },
        "display_description": {
            "type": "string",
            "description": "The volume description.",
        },
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the volume.",
        },
        "image_id": {
            "type": "string",
            "format": "uuid",
            "description": "The uuid for the new image.",
        },
        "image_name": {
            "type": "string",
            "description": "The name for the new image.",
        },
        "protected": {
            "type": "boolean",
            "description": "Whether the new image is protected. Default=False.",
            "x-openstack": {"min-ver": "3.1"},
        },
        "size": {
            "type": "integer",
            "format": "int64",
            "description": "The size of the volume, in gibibytes (GiB).",
        },
        "status": {"type": "integer", "description": "The volume status."},
        "updated_at": {
            "type": "string",
            "format": "date-time",
            "description": "The date and time when the resource was updated.",
        },
        "visibility": {
            "type": "string",
            "description": "The visibility property of the new image. Default is private.",
            "x-openstack": {"min-ver": "3.1"},
        },
        "volume_type": {
            "type": "string",
            "description": "The associated volume type name for the volume.",
        },
    },
}

VOLUME_TYPE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "The volume type description.",
        },
        "extra_specs": {
            "description": "A key and value pair that contains additional specifications that are associated with the volume type. Examples include capabilities, capacity, compression, and so on, depending on the storage driver in use.",
            **parameter_types.extra_specs_with_no_spaces_key,
        },
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the volume type.",
        },
        "is_public": {
            "type": "boolean",
            "description": "Whether the volume type is publicly visible.",
        },
        "name": {
            "type": "string",
            "description": "The volume type description.",
        },
        "os-volume-type-access:is_public": {
            "type": "boolean",
            "description": "Whether the volume type is publicly visible.",
        },
        "qos_specs_id": {
            "type": "string",
            "format": "uuid",
            "description": "The QoS specifications ID.",
        },
    },
}

VOLUME_TYPE_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"volume_type": VOLUME_TYPE_SCHEMA},
}

VOLUME_TYPES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "volume_types": {"type": "array", "items": VOLUME_TYPE_SCHEMA}
    },
}

VOLUME_TYPE_LIST_PARAMETERS: dict[str, Any] = {
    "type_is_public": {
        "in": "query",
        "name": "is_public",
        "description": "Filter the volume type by public visibility.",
        "schema": {"type": "boolean"},
    },
    "type_sort": {
        "in": "query",
        "name": "sort",
        "description": "Comma-separated list of sort keys and optional sort directions in the form of < key > [: < direction > ]. A valid direction is asc (ascending) or desc (descending).",
        "schema": {"type": "string"},
    },
    "type_sort_key": {
        "in": "query",
        "name": "sort_key",
        "description": "Sorts by an attribute. A valid value is name, status, container_format, disk_format, size, id, created_at, or updated_at. Default is created_at. The API uses the natural sorting direction of the sort_key attribute value. Deprecated in favour of the combined sort parameter.",
        "schema": {"type": "string"},
    },
    "type_sort_dir": {
        "in": "query",
        "name": "sort_dir",
        "description": "Sorts by one or more sets of attribute and sort direction combinations. If you omit the sort direction in a set, default is desc. Deprecated in favour of the combined sort parameter.",
        "schema": {"type": "string"},
    },
    "type_limit": {
        "in": "query",
        "name": "limit",
        "description": "Requests a page size of items. Returns a number of items up to a limit value. Use the limit parameter to make an initial limited request and use the ID of the last-seen item from the response as the marker parameter value in a subsequent limited request.",
        "schema": {"type": "integer"},
    },
    "type_marker": {
        "in": "query",
        "name": "marker",
        "description": "The ID of the last-seen item. Use the limit parameter to make an initial limited request and use the ID of the last-seen item from the response as the marker parameter value in a subsequent limited request.",
        "schema": {"type": "string"},
    },
    "type_offset": {
        "in": "query",
        "name": "offset",
        "description": "Used in conjunction with limit to return a slice of items. offset is where to start in the list.",
        "schema": {"type": "integer"},
    },
}

VOLUME_TYPE_EXTRA_SPECS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "extra_specs": {
            "description": "A key and value pair that contains additional specifications that are associated with the volume type. Examples include capabilities, capacity, compression, and so on, depending on the storage driver in use.",
            **parameter_types.extra_specs_with_no_spaces_key,
        },
    },
}

VOLUME_TYPE_EXTRA_SPEC_SCHEMA: dict[str, Any] = (
    parameter_types.extra_specs_with_no_spaces_key
)

VOLUME_TYPE_ACCESS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "volume_type_access": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "The UUID of the project.",
                    },
                    "volume_type_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "The UUID of the volume type.",
                    },
                },
            },
        }
    },
}

VOLUME_TYPE_ENCRYPTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cipher": {
            "type": "string",
            "description": "The encryption algorithm or mode. For example, aes-xts-plain64. The default value is None.",
        },
        "control_location": {
            "type": "string",
            "enum": ["front-end", "back-end"],
            "description": "Notional service where encryption is performed. Valid values are “front-end” or “back-end”. The default value is “front-end”.",
        },
        "created_at": {
            "type": "string",
            "format": "date-time",
            "description": "The date and time when the resource was created.",
        },
        "deleted": {
            "type": "boolean",
            "description": "The resource is deleted or not.",
        },
        "deleted_at": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "The date and time when the resource was deleted.",
        },
        "encryption_id": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the encryption.",
        },
        "key_size": {
            "type": "integer",
            "description": "Size of encryption key, in bits. This is usually 256. The default value is None.",
        },
        "provider": {
            "type": "string",
            "description": "The class that provides encryption support.",
        },
        "updated_at": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "The date and time when the resource was updated.",
        },
    },
}

VOLUME_TYPE_ENCRYPTION_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"encryption": VOLUME_TYPE_ENCRYPTION_SCHEMA},
}

VOLUME_TYPE_ENCRYPTION_SHOW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cipher": {
            "type": "string",
            "description": "The encryption algorithm or mode. For example, aes-xts-plain64. The default value is None.",
        },
    },
}
