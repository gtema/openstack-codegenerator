# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
from unittest import TestCase

from codegenerator import model


SAMPLE_SERVER_SCHEMA = {
    "type": "object",
    "properties": {
        "server": {
            "type": "object",
            "description": "A `server` object.",
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 255,
                    "format": "name",
                    "description": "dummy description",
                },
                "imageRef": {
                    "oneOf": [
                        {"type": "string", "format": "uuid"},
                        {"type": "string", "maxLength": 0},
                    ]
                },
                "flavorRef": {"type": ["string", "integer"], "minLength": 1},
                "adminPass": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "description": "metadata description",
                    "additionalProperties": False,
                    "patternProperties": {
                        "^[a-zA-Z0-9-_:. ]{1,255}$": {
                            "type": "string",
                            "maxLength": 255,
                        }
                    },
                },
                "networks": {
                    "oneOf": [
                        {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "fixed_ip": {
                                        "type": "string",
                                        "oneOf": [
                                            {"format": "ipv4"},
                                            {"format": "ipv6"},
                                        ],
                                    },
                                    "port": {
                                        "oneOf": [
                                            {
                                                "type": "string",
                                                "format": "uuid",
                                            },
                                            {"type": "null"},
                                        ]
                                    },
                                    "uuid": {
                                        "type": "string",
                                        "format": "uuid",
                                    },
                                    "tag": {
                                        "type": "string",
                                        "minLength": 1,
                                        "maxLength": 60,
                                        "pattern": "^[^,/]*$",
                                    },
                                },
                                "additionalProperties": False,
                            },
                        },
                        {"type": "string", "enum": ["none", "auto"]},
                    ],
                    "description": "Networks description",
                },
                "OS-DCF:diskConfig": {
                    "type": "string",
                    "enum": ["AUTO", "MANUAL"],
                    "description": "DiskConfig description",
                },
                "accessIPv4": {
                    "type": "string",
                    "format": "ipv4",
                    "description": "IPv4 address",
                },
                "availability_zone": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 255,
                    "format": "name",
                    "description": "A target cell name.",
                },
                "block_device_mapping": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "virtual_name": {
                                "type": "string",
                                "maxLength": 255,
                            },
                            "volume_id": {"type": "string", "format": "uuid"},
                            "snapshot_id": {
                                "type": "string",
                                "format": "uuid",
                            },
                            "volume_size": {
                                "type": ["integer", "string"],
                                "pattern": "^[0-9]+$",
                                "minimum": 1,
                                "maximum": 2147483647,
                            },
                            "device_name": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 255,
                                "pattern": "^[a-zA-Z0-9._-r/]*$",
                            },
                            "delete_on_termination": {
                                "type": ["boolean", "string"],
                                "enum": [
                                    True,
                                    "True",
                                    False,
                                    "False",
                                ],
                            },
                            "no_device": {},
                            "connection_info": {
                                "type": "string",
                                "maxLength": 16777215,
                            },
                        },
                        "additionalProperties": False,
                    },
                },
                "block_device_mapping_v2": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "virtual_name": {
                                "type": "string",
                                "maxLength": 255,
                            },
                            "volume_id": {"type": "string", "format": "uuid"},
                            "snapshot_id": {
                                "type": "string",
                                "format": "uuid",
                            },
                            "volume_size": {
                                "type": ["integer", "string"],
                                "pattern": "^[0-9]+$",
                                "minimum": 1,
                                "maximum": 2147483647,
                            },
                            "device_name": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 255,
                                "pattern": "^[a-zA-Z0-9._-r/]*$",
                            },
                            "delete_on_termination": {
                                "type": ["boolean", "string"],
                                "enum": [
                                    True,
                                    "True",
                                    False,
                                    "False",
                                ],
                            },
                            "no_device": {},
                            "connection_info": {
                                "type": "string",
                                "maxLength": 16777215,
                            },
                            "source_type": {
                                "type": "string",
                                "enum": [
                                    "volume",
                                    "image",
                                    "snapshot",
                                    "blank",
                                ],
                            },
                            "uuid": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 255,
                                "pattern": "^[a-zA-Z0-9._-]*$",
                            },
                            "image_id": {"type": "string", "format": "uuid"},
                            "destination_type": {
                                "type": "string",
                                "enum": ["local", "volume"],
                            },
                            "guest_format": {
                                "type": "string",
                                "maxLength": 255,
                            },
                            "device_type": {
                                "type": "string",
                                "maxLength": 255,
                            },
                            "disk_bus": {"type": "string", "maxLength": 255},
                            "boot_index": {
                                "type": ["integer", "string", "null"],
                                "pattern": "^-?[0-9]+$",
                            },
                            "tag": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 60,
                                "pattern": "^[^,/]*$",
                            },
                            "volume_type": {
                                "type": ["string", "null"],
                                "minLength": 0,
                                "maxLength": 255,
                            },
                        },
                        "additionalProperties": False,
                    },
                    "description": "descr",
                },
                "config_drive": {
                    "type": ["boolean", "string"],
                    "enum": ["No", "no", False],
                },
                "min_count": {
                    "type": ["integer", "string"],
                    "pattern": "^[0-9]*$",
                    "minimum": 1,
                    "minLength": 1,
                },
                "security_groups": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 255,
                                "format": "name",
                                "description": "A target cell name. Schedule the server in a host in the cell specified.",
                            }
                        },
                        "additionalProperties": False,
                    },
                    "description": "SG descr",
                },
                "user_data": {
                    "type": "string",
                    "format": "base64",
                    "maxLength": 65535,
                    "description": "user data",
                },
                "description": {
                    "type": ["string", "null"],
                    "minLength": 0,
                    "maxLength": 255,
                    "pattern": "regex_pattern",
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 60,
                        "pattern": "^[^,/]*$",
                    },
                    "maxItems": 50,
                },
                "trusted_image_certificates": {
                    "type": ["array", "null"],
                    "minItems": 1,
                    "maxItems": 50,
                    "uniqueItems": True,
                    "items": {"type": "string", "minLength": 1},
                },
                "host": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 255,
                    "pattern": "^[a-zA-Z0-9-._]*$",
                },
                "hypervisor_hostname": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 255,
                    "pattern": "^[a-zA-Z0-9-._]*$",
                },
                "hostname": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 255,
                    "pattern": "^[a-zA-Z0-9-._]*$",
                },
            },
            "additionalProperties": False,
            "required": ["name", "flavorRef", "networks"],
        },
        "os:scheduler_hints": {
            "type": "object",
            "description": "scheduler hints description",
            "properties": {
                "group": {"type": "string", "format": "uuid"},
                "different_host": {
                    "oneOf": [
                        {"type": "string", "format": "uuid"},
                        {
                            "type": "array",
                            "items": {"type": "string", "format": "uuid"},
                        },
                    ]
                },
                "same_host": {
                    "type": ["string", "array"],
                    "items": {"type": "string", "format": "uuid"},
                    "description": "A list of server UUIDs or a server UUID.",
                },
                "query": {"type": ["string", "object"]},
                "target_cell": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 255,
                    "format": "name",
                },
                "different_cell": {
                    "type": ["string", "array"],
                    "items": {"type": "string"},
                },
                "build_near_host_ip": {
                    "type": "string",
                    "oneOf": [{"format": "ipv4"}, {"format": "ipv6"}],
                    "description": "Schedule the server on a host in the network specified with",
                },
                "cidr": {"type": "string", "pattern": "^/[0-9a-f.:]+$"},
            },
            "additionalProperties": True,
        },
        "OS-SCH-HNT:scheduler_hints": {
            "type": "object",
            "properties": {
                "group": {"type": "string", "format": "uuid"},
                "different_host": {
                    "oneOf": [
                        {"type": "string", "format": "uuid"},
                        {
                            "type": "array",
                            "items": {"type": "string", "format": "uuid"},
                        },
                    ],
                    "description": "A list of server UUIDs or a server UUID.\nSchedule the server on a different host from a set of servers.\nIt is available when `DifferentHostFilter` is available on cloud side.",
                },
                "same_host": {
                    "type": ["string", "array"],
                    "items": {"type": "string", "format": "uuid"},
                },
                "query": {"type": ["string", "object"]},
                "target_cell": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 255,
                    "format": "name",
                },
                "different_cell": {
                    "type": ["string", "array"],
                    "items": {"type": "string"},
                },
                "build_near_host_ip": {
                    "type": "string",
                    "oneOf": [{"format": "ipv4"}, {"format": "ipv6"}],
                },
                "cidr": {"type": "string", "pattern": "^/[0-9a-f.:]+$"},
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": False,
    "x-openstack": {"min-ver": "2.94"},
    "required": ["server"],
}

EXPECTED_TLA_DATA = model.Struct(
    reference=None,
    fields={
        "server": model.StructField(
            data_type=model.Reference(name="server", type=model.Struct),
            description="A `server` object.",
            is_required=True,
        ),
        "os:scheduler_hints": model.StructField(
            data_type=model.Reference(
                name="os:scheduler_hints", type=model.Struct
            ),
            description="scheduler hints description",
        ),
        "OS-SCH-HNT:scheduler_hints": model.StructField(
            data_type=model.Reference(
                name="OS-SCH-HNT:scheduler_hints", type=model.Struct
            ),
        ),
    },
)

EXPECTED_DATA_TYPES = [
    model.OneOfType(
        reference=model.Reference(name="imageRef", type=model.OneOfType),
        kinds=[
            model.ConstraintString(format="uuid"),
            model.ConstraintString(maxLength=0),
        ],
    ),
    model.OneOfType(
        reference=model.Reference(name="flavorRef", type=model.OneOfType),
        kinds=[
            model.ConstraintString(minLength=1),
            model.ConstraintInteger(),
        ],
    ),
    model.Dictionary(
        reference=model.Reference(name="metadata", type=model.Dictionary),
        description="metadata description",
        value_type=model.ConstraintString(maxLength=255),
    ),
    model.OneOfType(
        reference=model.Reference(name="fixed_ip", type=model.OneOfType),
        kinds=[
            model.ConstraintString(format="ipv4"),
            model.ConstraintString(format="ipv6"),
        ],
    ),
    model.OneOfType(
        reference=model.Reference(name="port", type=model.OneOfType),
        kinds=[
            model.ConstraintString(format="uuid"),
            model.PrimitiveNull(),
        ],
    ),
    model.Struct(
        reference=model.Reference(name="networks", type=model.Struct),
        fields={
            "fixed_ip": model.StructField(
                data_type=model.Reference(
                    name="fixed_ip", type=model.OneOfType
                ),
            ),
            "port": model.StructField(
                data_type=model.Reference(name="port", type=model.OneOfType),
            ),
            "uuid": model.StructField(
                data_type=model.ConstraintString(format="uuid"),
            ),
            "tag": model.StructField(
                data_type=model.ConstraintString(
                    minLength=1, maxLength=60, pattern="^[^,/]*$"
                ),
            ),
        },
    ),
    model.Array(
        reference=model.Reference(name="networks", type=model.Array),
        item_type=model.Reference(name="networks", type=model.Struct),
    ),
    model.OneOfType(
        reference=model.Reference(name="networks", type=model.OneOfType),
        kinds=[
            model.Reference(name="networks", type=model.Array),
            model.Reference(name="networks", type=model.Enum),
        ],
    ),
    model.Enum(
        reference=model.Reference(name="networks", type=model.Enum),
        literals=["none", "auto"],
        base_types=[model.ConstraintString],
    ),
    model.OneOfType(
        reference=model.Reference(name="volume_size", type=model.OneOfType),
        kinds=[
            model.ConstraintInteger(minimum=1, maximum=2147483647),
            model.ConstraintString(pattern="^[0-9]+$"),
        ],
    ),
    # model.OneOfType(
    #    reference=model.Reference(
    #        name="delete_on_termination", type=model.OneOfType
    #    ),
    #    kinds=[
    #        model.Reference(name="delete_on_termination", type=model.Enum)
    #        #model.PrimitiveBoolean(), model.ConstraintString()
    #    ],
    # ),
    model.Enum(
        reference=model.Reference(
            name="delete_on_termination", type=model.Enum
        ),
        literals=[True, "True", False, "False"],
        base_types=[model.ConstraintString, model.PrimitiveBoolean],
    ),
    model.Struct(
        reference=model.Reference(
            name="block_device_mapping", type=model.Struct
        ),
        fields={
            "virtual_name": model.StructField(
                data_type=model.ConstraintString(maxLength=255),
            ),
            "volume_id": model.StructField(
                data_type=model.ConstraintString(format="uuid"),
            ),
            "snapshot_id": model.StructField(
                data_type=model.ConstraintString(format="uuid"),
            ),
            "volume_size": model.StructField(
                data_type=model.Reference(
                    name="volume_size", type=model.OneOfType
                ),
            ),
            "device_name": model.StructField(
                data_type=model.ConstraintString(
                    minLength=1,
                    maxLength=255,
                    pattern="^[a-zA-Z0-9._-r/]*$",
                ),
            ),
            "delete_on_termination": model.StructField(
                data_type=model.Reference(
                    name="delete_on_termination", type=model.Enum
                ),
            ),
            "no_device": model.StructField(
                data_type=model.PrimitiveNull(),
            ),
            "connection_info": model.StructField(
                data_type=model.ConstraintString(maxLength=16777215),
            ),
        },
    ),
    model.OneOfType(
        reference=model.Reference(name="volume_size", type=model.OneOfType),
        kinds=[
            model.ConstraintInteger(minimum=1, maximum=2147483647),
            model.ConstraintString(pattern="^[0-9]+$"),
        ],
    ),
    model.OneOfType(
        reference=model.Reference(name="boot_index", type=model.OneOfType),
        kinds=[
            model.ConstraintInteger(),
            model.ConstraintString(pattern="^-?[0-9]+$"),
            model.PrimitiveNull(),
        ],
    ),
    model.OneOfType(
        reference=model.Reference(name="volume_type", type=model.OneOfType),
        kinds=[
            model.ConstraintString(minLength=0, maxLength=255),
            model.PrimitiveNull(),
        ],
    ),
    model.Struct(
        reference=model.Reference(
            name="block_device_mapping_v2", type=model.Struct
        ),
        fields={
            "virtual_name": model.StructField(
                data_type=model.ConstraintString(maxLength=255),
            ),
            "volume_id": model.StructField(
                data_type=model.ConstraintString(
                    format="uuid",
                ),
            ),
            "snapshot_id": model.StructField(
                data_type=model.ConstraintString(
                    format="uuid",
                ),
            ),
            "volume_size": model.StructField(
                data_type=model.Reference(
                    name="volume_size", type=model.OneOfType
                ),
            ),
            "device_name": model.StructField(
                data_type=model.ConstraintString(
                    minLength=1,
                    maxLength=255,
                    pattern="^[a-zA-Z0-9._-r/]*$",
                ),
            ),
            "delete_on_termination": model.StructField(
                data_type=model.Reference(
                    name="delete_on_termination", type=model.Enum
                ),
            ),
            "no_device": model.StructField(
                data_type=model.PrimitiveNull(),
            ),
            "connection_info": model.StructField(
                data_type=model.ConstraintString(
                    maxLength=16777215,
                ),
            ),
            "source_type": model.StructField(
                data_type=model.Reference(name="source_type", type=model.Enum)
            ),
            "uuid": model.StructField(
                data_type=model.ConstraintString(
                    minLength=1,
                    maxLength=255,
                    pattern="^[a-zA-Z0-9._-]*$",
                ),
            ),
            "image_id": model.StructField(
                data_type=model.ConstraintString(
                    format="uuid",
                ),
            ),
            "destination_type": model.StructField(
                data_type=model.Reference(
                    name="destination_type", type=model.Enum
                )
            ),
            "guest_format": model.StructField(
                data_type=model.ConstraintString(
                    maxLength=255,
                ),
            ),
            "device_type": model.StructField(
                data_type=model.ConstraintString(
                    maxLength=255,
                ),
            ),
            "disk_bus": model.StructField(
                data_type=model.ConstraintString(
                    maxLength=255,
                ),
            ),
            "boot_index": model.StructField(
                data_type=model.Reference(
                    name="boot_index", type=model.OneOfType
                ),
            ),
            "tag": model.StructField(
                data_type=model.ConstraintString(
                    minLength=1,
                    maxLength=60,
                    pattern="^[^,/]*$",
                ),
            ),
            "volume_type": model.StructField(
                data_type=model.Reference(
                    name="volume_type", type=model.OneOfType
                ),
            ),
        },
    ),
    model.Array(
        reference=model.Reference(
            name="block_device_mapping", type=model.Array
        ),
        item_type=model.Reference(
            name="block_device_mapping", type=model.Struct
        ),
    ),
    model.Array(
        reference=model.Reference(
            name="block_device_mapping_v2", type=model.Array
        ),
        item_type=model.Reference(
            name="block_device_mapping_v2", type=model.Struct
        ),
    ),
    model.Enum(
        reference=model.Reference(name="config_drive", type=model.Enum),
        base_types=[
            model.PrimitiveBoolean,
            model.ConstraintString,
        ],
        literals=set(["No", "no", False]),
    ),
    model.OneOfType(
        reference=model.Reference(name="min_count", type=model.OneOfType),
        kinds=[
            model.ConstraintInteger(
                minimum=1,
            ),
            model.ConstraintString(
                minLength=1,
                pattern="^[0-9]*$",
            ),
        ],
    ),
    model.Struct(
        reference=model.Reference(name="security_groups", type=model.Struct),
        fields={
            "name": model.StructField(
                data_type=model.ConstraintString(
                    format="name", minLength=1, maxLength=255
                ),
                description="A target cell name. Schedule the server in a host in the cell specified.",
            )
        },
    ),
    model.Array(
        reference=model.Reference(name="security_groups", type=model.Array),
        item_type=model.Reference(name="security_groups", type=model.Struct),
    ),
    model.OneOfType(
        reference=model.Reference(name="description", type=model.OneOfType),
        kinds=[
            model.ConstraintString(
                minLength=0,
                maxLength=255,
                pattern="regex_pattern",
            ),
            model.PrimitiveNull(),
        ],
    ),
    model.Array(
        reference=model.Reference(name="tags", type=model.Array),
        item_type=model.ConstraintString(
            format=None, minLength=1, maxLength=60, pattern="^[^,/]*$"
        ),
    ),
    model.Array(
        reference=model.Reference(
            name="trusted_image_certificates", type=model.Array
        ),
        item_type=model.ConstraintString(format=None, minLength=1),
    ),
    model.OneOfType(
        reference=model.Reference(
            name="trusted_image_certificates", type=model.OneOfType
        ),
        kinds=[
            model.Reference(
                name="trusted_image_certificates", type=model.Array
            ),
            model.PrimitiveNull(),
        ],
    ),
    model.Struct(
        reference=model.Reference(name="server", type=model.Struct),
        description="A `server` object.",
        fields={
            "name": model.StructField(
                data_type=model.ConstraintString(
                    format="name", minLength=1, maxLength=255
                ),
                description="dummy description",
                is_required=True,
            ),
            "imageRef": model.StructField(
                data_type=model.Reference(
                    name="imageRef", type=model.OneOfType
                ),
            ),
            "flavorRef": model.StructField(
                data_type=model.Reference(
                    name="flavorRef", type=model.OneOfType
                ),
                is_required=True,
            ),
            "adminPass": model.StructField(
                data_type=model.ConstraintString(format=None),
            ),
            "metadata": model.StructField(
                data_type=model.Reference(
                    name="metadata", type=model.Dictionary
                ),
                description="metadata description",
            ),
            "networks": model.StructField(
                data_type=model.Reference(
                    name="networks", type=model.OneOfType
                ),
                description="Networks description",
                is_required=True,
            ),
            "OS-DCF:diskConfig": model.StructField(
                data_type=model.Reference(
                    name="OS-DCF:diskConfig", type=model.Enum
                ),
                description="DiskConfig description",
            ),
            "accessIPv4": model.StructField(
                data_type=model.ConstraintString(format="ipv4"),
                description="IPv4 address",
            ),
            "availability_zone": model.StructField(
                data_type=model.ConstraintString(
                    format="name", minLength=1, maxLength=255
                ),
                description="A target cell name.",
            ),
            "block_device_mapping": model.StructField(
                data_type=model.Reference(
                    name="block_device_mapping", type=model.Array
                ),
            ),
            "block_device_mapping_v2": model.StructField(
                data_type=model.Reference(
                    name="block_device_mapping_v2", type=model.Array
                ),
                description="descr",
            ),
            "config_drive": model.StructField(
                data_type=model.Reference(
                    name="config_drive", type=model.Enum
                ),
            ),
            "min_count": model.StructField(
                data_type=model.Reference(
                    name="min_count", type=model.OneOfType
                ),
            ),
            "security_groups": model.StructField(
                data_type=model.Reference(
                    name="security_groups", type=model.Array
                ),
                description="SG descr",
            ),
            "user_data": model.StructField(
                data_type=model.ConstraintString(
                    format="base64",
                    maxLength=65535,
                ),
                description="user data",
            ),
            "description": model.StructField(
                data_type=model.Reference(
                    name="description", type=model.OneOfType
                ),
            ),
            "tags": model.StructField(
                data_type=model.Reference(name="tags", type=model.Array),
            ),
            "trusted_image_certificates": model.StructField(
                data_type=model.Reference(
                    name="trusted_image_certificates", type=model.OneOfType
                ),
            ),
            "host": model.StructField(
                data_type=model.ConstraintString(
                    minLength=1,
                    maxLength=255,
                    pattern="^[a-zA-Z0-9-._]*$",
                ),
            ),
            "hypervisor_hostname": model.StructField(
                data_type=model.ConstraintString(
                    minLength=1,
                    maxLength=255,
                    pattern="^[a-zA-Z0-9-._]*$",
                ),
            ),
            "hostname": model.StructField(
                data_type=model.ConstraintString(
                    minLength=1,
                    maxLength=255,
                    pattern="^[a-zA-Z0-9-._]*$",
                ),
            ),
        },
    ),
    model.Array(
        reference=model.Reference(name="different_host", type=model.Array),
        item_type=model.ConstraintString(format="uuid"),
    ),
    model.OneOfType(
        reference=model.Reference(name="different_host", type=model.OneOfType),
        kinds=[
            model.ConstraintString(format="uuid"),
            model.Reference(name="different_host", type=model.Array),
        ],
    ),
    model.Array(
        reference=model.Reference(name="same_host", type=model.Array),
        item_type=model.ConstraintString(format="uuid"),
    ),
    model.OneOfType(
        reference=model.Reference(name="same_host", type=model.OneOfType),
        kinds=[
            model.ConstraintString(format=None),
            model.Reference(name="same_host", type=model.Array),
        ],
    ),
    model.Dictionary(
        reference=model.Reference(name="query", type=model.Dictionary),
        value_type=model.PrimitiveAny(),
    ),
    model.OneOfType(
        reference=model.Reference(name="query", type=model.OneOfType),
        kinds=[
            model.ConstraintString(format=None),
            model.Reference(name="query", type=model.Dictionary),
        ],
    ),
    model.Array(
        reference=model.Reference(name="different_cell", type=model.Array),
        item_type=model.ConstraintString(format=None),
    ),
    model.OneOfType(
        reference=model.Reference(name="different_cell", type=model.OneOfType),
        kinds=[
            model.ConstraintString(format=None),
            model.Reference(name="different_cell", type=model.Array),
        ],
    ),
    model.OneOfType(
        reference=model.Reference(
            name="build_near_host_ip", type=model.OneOfType
        ),
        kinds=[
            model.ConstraintString(format="ipv4"),
            model.ConstraintString(format="ipv6"),
        ],
    ),
    model.Struct(
        reference=model.Reference(
            name="os:scheduler_hints", type=model.Struct
        ),
        description="scheduler hints description",
        fields={
            "group": model.StructField(
                data_type=model.ConstraintString(format="uuid"),
            ),
            "different_host": model.StructField(
                data_type=model.Reference(
                    name="different_host", type=model.OneOfType
                ),
            ),
            "same_host": model.StructField(
                data_type=model.Reference(
                    name="same_host", type=model.OneOfType
                ),
                description="A list of server UUIDs or a server UUID.",
            ),
            "query": model.StructField(
                data_type=model.Reference(name="query", type=model.OneOfType),
            ),
            "target_cell": model.StructField(
                data_type=model.ConstraintString(
                    format="name", minLength=1, maxLength=255
                ),
            ),
            "different_cell": model.StructField(
                data_type=model.Reference(
                    name="different_cell", type=model.OneOfType
                ),
            ),
            "build_near_host_ip": model.StructField(
                data_type=model.Reference(
                    name="build_near_host_ip", type=model.OneOfType
                ),
                description="Schedule the server on a host in the network specified with",
            ),
            "cidr": model.StructField(
                data_type=model.ConstraintString(
                    pattern="^/[0-9a-f.:]+$",
                ),
            ),
        },
        additional_fields=model.PrimitiveAny(),
    ),
    model.Array(
        reference=model.Reference(name="different_host", type=model.Array),
        item_type=model.ConstraintString(format="uuid"),
    ),
    model.OneOfType(
        reference=model.Reference(name="different_host", type=model.OneOfType),
        kinds=[
            model.ConstraintString(format="uuid"),
            model.Reference(name="different_host", type=model.Array),
        ],
    ),
    model.Array(
        reference=model.Reference(name="same_host", type=model.Array),
        item_type=model.ConstraintString(format="uuid"),
    ),
    model.OneOfType(
        reference=model.Reference(name="same_host", type=model.OneOfType),
        kinds=[
            model.ConstraintString(format=None),
            model.Reference(name="same_host", type=model.Array),
        ],
    ),
    model.Array(
        reference=model.Reference(name="different_cell", type=model.Array),
        item_type=model.ConstraintString(format=None),
    ),
    model.OneOfType(
        reference=model.Reference(name="different_cell", type=model.OneOfType),
        kinds=[
            model.ConstraintString(format=None),
            model.Reference(name="different_cell", type=model.Array),
        ],
    ),
    model.Enum(
        reference=model.Reference(name="source_type", type=model.Enum),
        literals=set(["volume", "image", "snapshot", "blank"]),
        base_types=[
            model.ConstraintString,
        ],
    ),
    model.Enum(
        reference=model.Reference(name="destination_type", type=model.Enum),
        literals=set(["volume", "local"]),
        base_types=[
            model.ConstraintString,
        ],
    ),
    model.Enum(
        reference=model.Reference(name="OS-DCF:diskConfig", type=model.Enum),
        literals=set(["AUTO", "MANUAL"]),
        base_types=[
            model.ConstraintString,
        ],
    ),
    model.OneOfType(
        reference=model.Reference(
            name="build_near_host_ip", type=model.OneOfType
        ),
        kinds=[
            model.ConstraintString(format="ipv4"),
            model.ConstraintString(format="ipv6"),
        ],
    ),
    model.Struct(
        reference=model.Reference(
            name="OS-SCH-HNT:scheduler_hints", type=model.Struct
        ),
        fields={
            "group": model.StructField(
                data_type=model.ConstraintString(format="uuid"),
            ),
            "different_host": model.StructField(
                data_type=model.Reference(
                    name="different_host", type=model.OneOfType
                ),
                description="A list of server UUIDs or a server UUID.\nSchedule the server on a different host from a set of servers.\nIt is available when `DifferentHostFilter` is available on cloud side.",
            ),
            "same_host": model.StructField(
                data_type=model.Reference(
                    name="same_host", type=model.OneOfType
                ),
            ),
            "query": model.StructField(
                data_type=model.Reference(name="query", type=model.OneOfType),
            ),
            "target_cell": model.StructField(
                data_type=model.ConstraintString(
                    format="name", minLength=1, maxLength=255
                ),
            ),
            "different_cell": model.StructField(
                data_type=model.Reference(
                    name="different_cell", type=model.OneOfType
                ),
            ),
            "build_near_host_ip": model.StructField(
                data_type=model.Reference(
                    name="build_near_host_ip", type=model.OneOfType
                ),
            ),
            "cidr": model.StructField(
                data_type=model.ConstraintString(
                    pattern="^/[0-9a-f.:]+$",
                ),
            ),
        },
        additional_fields=model.PrimitiveAny(),
    ),
    EXPECTED_TLA_DATA,
]


class TestModel(TestCase):
    def test_model_parse(self):
        parser = model.JsonSchemaParser()
        (res, types) = parser.parse(SAMPLE_SERVER_SCHEMA)
        self.assertEqual(res, EXPECTED_TLA_DATA)
        for expected in EXPECTED_DATA_TYPES:
            if expected not in types:
                for present in types:
                    if present.reference and expected.reference:
                        if (
                            present.reference.name == expected.reference.name
                            and present.reference.type
                            == expected.reference.type
                        ):
                            self.assertEqual(expected, present)
                            break

    def test_parse_string_parameter(self):
        schema = {
            "in": "query",
            "name": "tags",
            "schema": {
                "type": "string",
                "format": "regex",
            },
            "x-openstack": {"min-ver": "2.26"},
        }
        parser = model.OpenAPISchemaParser()
        res = parser.parse_parameter(schema)
        dt = res.data_type
        self.assertIsInstance(res, model.RequestParameter)
        self.assertIsInstance(dt, model.ConstraintString)
        self.assertEqual("regex", dt.format)
        self.assertEqual("query", res.location)
        self.assertEqual("tags", res.name)

    def test_parse_string_array_parameter(self):
        schema = {
            "in": "query",
            "name": "tags",
            "schema": {"type": "array", "items": {"type": "string"}},
            "style": "form",
            "explode": False,
        }
        parser = model.OpenAPISchemaParser()
        res = parser.parse_parameter(schema)
        dt = res.data_type
        self.assertIsInstance(res, model.RequestParameter)
        self.assertIsInstance(dt, model.CommaSeparatedList)
        self.assertIsInstance(dt.item_type, model.ConstraintString)

    def test_parse_limit_multitype_parameter(self):
        schema = {
            "in": "query",
            "name": "limit",
            "schema": {
                "type": ["strng", "integer"],
                "format": "^[0-9]*$",
                "minimum": 0,
            },
        }
        parser = model.OpenAPISchemaParser()
        res = parser.parse_parameter(schema)
        dt = res.data_type
        self.assertIsInstance(res, model.RequestParameter)
        self.assertIsInstance(dt, model.ConstraintInteger)
        self.assertEqual(dt.minimum, 0)
