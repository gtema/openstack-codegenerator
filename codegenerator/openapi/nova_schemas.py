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

from nova.api.openstack.compute.schemas import flavors_extraspecs
from nova.api.openstack.compute.schemas import quota_sets
from nova.api.openstack.compute.schemas import remote_consoles
from nova.api.validation import parameter_types

# NOTE(gtema): This is a temporary location for schemas not currently defined
# in Nova. Once everything is stabilized those must be moved directly to Nova

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


SERVER_TAGS_SCHEMA: dict[str, Any] = {
    "description": "Server Tags",
    "type": "object",
    "properties": {
        "tags": {
            "type": "array",
            "description": "A list of tags. The maximum count of tags in this list is 50.",
            "items": {
                "type": "string",
            },
        }
    },
}

SERVER_TOPOLOGY_SCHEMA: dict[str, Any] = {
    "description": "NUMA topology information for a server",
    "type": "object",
    "properties": {
        "nodes": {
            "description": "NUMA nodes information of a server",
            "type": "array",
            "items": {
                "type": "object",
                "description": "NUMA node information of a server",
                "properties": {
                    "cpu_pinning": {
                        "type": "object",
                        "description": "The mapping of server cores to host physical CPU",
                        "additionalProperties": {
                            "type": "integer",
                        },
                    },
                    "vcpu_set": {
                        "type": "array",
                        "description": "A list of IDs of the virtual CPU assigned to this NUMA node.",
                        "items": {"type": "integer"},
                    },
                    "siblings": {
                        "type": "array",
                        "description": "A mapping of host cpus thread sibling.",
                        "items": {"type": "integer"},
                    },
                    "memory_mb": {
                        "type": "integer",
                        "description": "The amount of memory assigned to this NUMA node in MB.",
                    },
                    "host_node": {
                        "type": "integer",
                        "description": "The host NUMA node the virtual NUMA node is map to.",
                    },
                    "pagesize_kb": {
                        "type": ["integer", "null"],
                        "description": "The page size in KB of a server. This field is null if the page size information is not available.",
                    },
                },
            },
        }
    },
}

FLAVOR_EXTRA_SPEC_SCHEMA: dict[str, Any] = {
    "minProperties": 1,
    "maxProperties": 1,
    "examples": {"JSON Request": {"hw:numa_nodes": "1"}},
    **flavors_extraspecs.metadata,
}

FLAVOR_EXTRA_SPECS_SCHEMA: dict[str, Any] = flavors_extraspecs.metadata
FLAVOR_EXTRA_SPECS_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "A dictionary of the flavor’s extra-specs key-and-value pairs. It appears in the os-extra-specs’ “create” REQUEST body, as well as the os-extra-specs’ “create” and “list” RESPONSE body.",
    "properties": {"extra_specs": flavors_extraspecs.metadata},
}

FLAVOR_SHORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "links": LINKS_SCHEMA,
    },
}
FLAVOR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "The display name of a flavor.",
        },
        "id": {
            "type": "string",
            "description": "The ID of the flavor. While people often make this look like an int, this is really a string.",
            "minLength": 1,
            "maxLength": 255,
            "pattern": "^(?! )[a-zA-Z0-9. _-]+(?<! )$",
        },
        "ram": {
            "description": "The amount of RAM a flavor has, in MiB.",
            **parameter_types.flavor_param_positive,
        },
        "vcpus": {
            "description": "The number of virtual CPUs that will be allocated to the server.",
            **parameter_types.flavor_param_positive,
        },
        "disk": {
            "description": "The size of the root disk that will be created in GiB. If 0 the root disk will be set to exactly the size of the image used to deploy the instance. However, in this case the scheduler cannot select the compute host based on the virtual image size. Therefore, 0 should only be used for volume booted instances or for testing purposes. Volume-backed instances can be enforced for flavors with zero root disk via the os_compute_api:servers:create:zero_disk_flavor policy rule.",
            **parameter_types.flavor_param_non_negative,
        },
        "OS-FLV-EXT-DATA:ephemeral": {
            "description": "The size of the ephemeral disk that will be created, in GiB. Ephemeral disks may be written over on server state changes. So should only be used as a scratch space for applications that are aware of its limitations. Defaults to 0.",
            **parameter_types.flavor_param_non_negative,
        },
        "swap": {
            "description": "The size of a dedicated swap disk that will be allocated, in MiB. If 0 (the default), no dedicated swap disk will be created. Currently, the empty string (‘’) is used to represent 0. As of microversion 2.75 default return value of swap is 0 instead of empty string.",
            **parameter_types.flavor_param_non_negative,
        },
        "rxtx_factor": {
            "description": "The receive / transmit factor (as a float) that will be set on ports if the network backend supports the QOS extension. Otherwise it will be ignored. It defaults to 1.0.",
            "type": ["number", "string"],
            "pattern": r"^[0-9]+(\.[0-9]+)?$",
            "minimum": 0,
            "exclusiveMinimum": True,
            "maximum": 3.40282e38,
        },
        "os-flavor-access:is_public": {
            "description": "Whether the flavor is public (available to all projects) or scoped to a set of projects. Default is True if not specified.",
            **parameter_types.boolean,
        },
        "extra_specs": FLAVOR_EXTRA_SPECS_SCHEMA,
        "links": LINKS_SCHEMA,
    },
    "additionalProperties": False,
}

FLAVOR_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Single flavor details",
    "properties": {"flavor": copy.deepcopy(FLAVOR_SCHEMA)},
}

FLAVORS_LIST_SCHEMA: dict[str, Any] = {
    "description": "Flavors list response",
    "type": "object",
    "properties": {
        "flavors": {
            "type": "array",
            "items": copy.deepcopy(FLAVOR_SHORT_SCHEMA),
        }
    },
}

FLAVORS_LIST_DETAIL_SCHEMA: dict[str, Any] = {
    "description": "Detailed flavors list response",
    "type": "object",
    "properties": {
        "flavors": {"type": "array", "items": copy.deepcopy(FLAVOR_SCHEMA)}
    },
}

FLAVOR_ACCESS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "flavor_id": {"type": "string", "format": "uuid"},
        "tenant_id": {"type": "string", "format": "uuid"},
    },
}
FLAVOR_ACCESSES_SCHEMA: dict[str, Any] = {
    "description": "A list of objects, each with the keys flavor_id and tenant_id.",
    "type": "object",
    "properties": {
        "flavor_access": {
            "type": "array",
            "items": copy.deepcopy(FLAVOR_ACCESS_SCHEMA),
        }
    },
}

LIMITS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Data structure that contains both absolute limits within a deployment.",
    "properties": {
        "absolute": {
            "type": "object",
            "properties": {
                "maxServerGroupMembers": {
                    "type": "integer",
                    "description": "The number of allowed members for each server group.",
                },
                "maxServerGroups": {
                    "type": "integer",
                    "description": "The number of allowed server groups for each tenant.",
                },
                "maxServerMetamaxServerMeta": {
                    "type": "integer",
                    "description": "The number of allowed metadata items for each server.",
                },
                "maxTotalCores": {
                    "type": "integer",
                    "description": "The number of allowed server cores for each tenant.",
                },
                "maxTotalInstances": {
                    "type": "integer",
                    "description": "The number of allowed servers for each tenant.",
                },
                "maxTotalKeypairs": {
                    "type": "integer",
                    "description": "The number of allowed key pairs for each user.",
                },
                "maxTotalRAMSize": {
                    "type": "integer",
                    "description": "The amount of allowed server RAM, in MiB, for each tenant.",
                },
                "totalCoresUsed": {
                    "type": "integer",
                    "description": "The number of used server cores in each tenant. If reserved query parameter is specified and it is not 0, the number of reserved server cores are also included.",
                },
                "totalInstancesUsed": {
                    "type": "integer",
                    "description": "The number of servers in each tenant. If reserved query parameter is specified and it is not 0, the number of reserved servers are also included.",
                },
                "totalRAMUsed": {
                    "type": "integer",
                    "description": "The amount of used server RAM in each tenant. If reserved query parameter is specified and it is not 0, the amount of reserved server RAM is also included.",
                },
                "totalServerGroupsUsed": {
                    "type": "integer",
                    "description": "The number of used server groups in each tenant. If reserved query parameter is specified and it is not 0, the number of reserved server groups are also included.",
                },
            },
            "additionalProperties": {"type": "integer"},
        },
    },
}

AGGREGATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "The host aggregate object",
    "properties": {
        "availability_zone": {
            "type": "string",
            "description": "The availability zone of the host aggregate.",
        },
        "created_at": {
            "type": "string",
            "format": "date-time",
            "description": "The date and time when the resource was created.",
        },
        "deleted": {
            "type": "boolean",
            "description": "A boolean indicates whether this aggregate is deleted or not, if it has not been deleted, false will appear.",
        },
        "deleted_at": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "The date and time when the resource was deleted. If the resource has not been deleted yet, this field will be null.",
        },
        "id": {
            "type": "integer",
            "description": "The ID of the host aggregate.",
        },
        "metadata": parameter_types.metadata,
        "hosts": {
            "type": "array",
            "description": "A list of host ids in this aggregate.",
            "items": {"type": "string"},
        },
        "updated_at": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "The date and time when the resource was updated, if the resource has not been updated, this field will show as null.",
        },
        "uuid": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the host aggregate. New in version 2.41",
            "x-openstack": {"min-ver": "2.41"},
        },
    },
}

AGGREGATE_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Aggregate object.",
    "properties": {"aggregate": copy.deepcopy(AGGREGATE_SCHEMA)},
}


AGGREGATE_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "The list of existing aggregates.",
    "properties": {
        "aggregates": {
            "type": "array",
            "description": "The list of existing aggregates.",
            "items": copy.deepcopy(AGGREGATE_SCHEMA),
        }
    },
}

VOLUME_SNAPSHOT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "A partial representation of a snapshot that is used to create a snapshot.",
    "properties": {
        "snapshot": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Its the same arbitrary string which was sent in request body.",
                },
                "volumeId": {
                    "type": "string",
                    "format": "uuid",
                    "description": "The source volume ID.",
                },
            },
        }
    },
}

AZ_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "zoneName": {
            "type": "string",
            "description": "The availability zone name.",
        },
        "zoneState": {
            "type": "object",
            "description": "The current state of the availability zone.",
            "properties": {
                "available": {
                    "type": "boolean",
                    "description": "Returns true if the availability zone is available.",
                }
            },
        },
        "hosts": {"type": "null", "description": "It is always null."},
    },
}

AZ_DETAIL_SCHEMA: dict[str, Any] = copy.deepcopy(AZ_SCHEMA)
AZ_DETAIL_SCHEMA["properties"]["hosts"] = {
    "type": "object",
    "description": "An object containing a list of host information. The host information is comprised of host and service objects. The service object returns three parameters representing the states of the service: active, available, and updated_at.",
    "examples": {
        "JSON request": {
            "conductor": {
                "nova-conductor": {
                    "active": True,
                    "available": True,
                    "updated_at": None,
                }
            },
            "scheduler": {
                "nova-scheduler": {
                    "active": True,
                    "available": True,
                    "updated_at": None,
                }
            },
        }
    },
}

AZ_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "availabilityZoneInfo": {
            "type": "array",
            "description": "The list of availability zone information.",
            "items": copy.deepcopy(AZ_SCHEMA),
        }
    },
}
AZ_LIST_DETAIL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "availabilityZoneInfo": {
            "type": "array",
            "description": "The list of availability zone information.",
            "items": copy.deepcopy(AZ_DETAIL_SCHEMA),
        }
    },
}

CONSOLE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Show Console Connection Information Response",
    "properties": {
        "console": {
            "type": "object",
            "description": "The console object.",
            "properties": {
                "instance_uuid": {
                    "type": "string",
                    "format": "uuid",
                    "description": "The UUID of the server.",
                },
                "host": {
                    "type": "string",
                    "description": "The name or ID of the host.",
                },
                "port": {"type": "integer", "description": "The port number."},
                "internal_access_path": {
                    "type": "string",
                    "description": "The id representing the internal access path.",
                },
            },
            "required": ["instance_uuid", "port"],
        }
    },
}

REMOTE_CONSOLE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Create Console Response",
    "properties": {
        "remote_console": {
            "type": "object",
            "description": "The remote console object.",
            "properties": {
                "protocol": {
                    "type": "string",
                    "enum": remote_consoles.create_v28["properties"][
                        "remote_console"
                    ]["properties"]["protocol"]["enum"],
                    "description": "The protocol of remote console. The valid values are vnc, spice, rdp, serial and mks. The protocol mks is added since Microversion 2.8.",
                },
                "type": {
                    "type": "string",
                    "enum": remote_consoles.create_v28["properties"][
                        "remote_console"
                    ]["properties"]["type"]["enum"],
                    "description": "The type of remote console. The valid values are novnc, rdp-html5, spice-html5, serial, and webmks. The type webmks is added since Microversion 2.8.",
                },
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": "The URL is used to connect the console.",
                },
            },
        }
    },
}

HYPERVISOR_SHORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "The hypervisor object.",
    "properties": {
        "hypervisor_hostname": {
            "type": "string",
            "description": "The hypervisor host name provided by the Nova virt driver. For the Ironic driver, it is the Ironic node uuid.",
        },
        "id": {
            "type": "string",
            "description": "The id of the hypervisor. From version 2.53 it is a string as UUID",
        },
        "state": {
            "type": "string",
            "enum": ["up", "down"],
            "description": "The state of the hypervisor.",
        },
        "status": {
            "type": "string",
            "enum": ["disabled", "enabled"],
            "description": "The status of the hypervisor.",
        },
        "servers": {
            "type": "array",
            "description": "A list of server objects. This field has become mandatory in microversion 2.75. If no servers is on hypervisor then empty list is returned. New in version 2.53",
            "x-openstack": {"min-ver": "2.53"},
            "items": {
                "type": "object",
                "properties": {
                    "uuid": {
                        "type": "string",
                        "format": "uuid",
                        "description": "The server ID.",
                    },
                    "name": {
                        "type": "string",
                        "description": "The server name.",
                    },
                },
            },
        },
    },
}

HYPERVISOR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "The hypervisor object.",
    "properties": {
        "cpu_info": {
            "type": "object",
            "description": "A dictionary that contains cpu information like arch, model, vendor, features and topology. The content of this field is hypervisor specific.",
            "additionalProperties": True,
            "x-openstack": {"max-ver": "2.87"},
        },
        "current_workload": {
            "type": "integer",
            "description": "The current_workload is the number of tasks the hypervisor is responsible for. This will be equal or greater than the number of active VMs on the system (it can be greater when VMs are being deleted and the hypervisor is still cleaning up). Available until version 2.87",
            "x-openstack": {"max-ver": "2.87"},
        },
        "disk_available_least": {
            "type": "integer",
            "description": "The actual free disk on this hypervisor(in GiB). If allocation ratios used for overcommit are configured, this may be negative. This is intentional as it provides insight into the amount by which the disk is overcommitted. Available until version 2.87",
            "x-openstack": {"max-ver": "2.87"},
        },
        "host_ip": {
            "type": "string",
            "format": "ip",
            "description": "The IP address of the hypervisor’s host.",
        },
        "free_disk_gb": {
            "type": "integer",
            "description": "The free disk remaining on this hypervisor(in GiB). This does not take allocation ratios used for overcommit into account so this value may be negative. Available until version 2.87",
            "x-openstack": {"max-ver": "2.87"},
        },
        "free_ram_mb": {
            "type": "integer",
            "description": "The free RAM in this hypervisor(in MiB). This does not take allocation ratios used for overcommit into account so this value may be negative. Available until version 2.87",
            "x-openstack": {"max-ver": "2.87"},
        },
        "hypervisor_hostname": {
            "type": "string",
            "description": "The hypervisor host name provided by the Nova virt driver. For the Ironic driver, it is the Ironic node uuid.",
        },
        "hypervisor_type": {
            "type": "string",
            "description": "The hypervisor type.",
        },
        "hypervisor_version": {
            "type": "integer",
            "description": "The hypervisor version.",
        },
        "local_gb": {
            "type": "integer",
            "x-openstack": {
                "max-ver": "2.87",
                "description": "The disk in this hypervisor (in GiB). This does not take allocation ratios used for overcommit into account so there may be disparity between this and the used count.",
            },
        },
        "local_gb_used": {
            "type": "integer",
            "x-openstack": {
                "max-ver": "2.87",
                "description": "The disk used in this hypervisor (in GiB).",
            },
        },
        "memory_mb": {
            "type": "integer",
            "x-openstack": {
                "max-ver": "2.87",
                "description": "The memory of this hypervisor (in MiB). This does not take allocation ratios used for overcommit into account so there may be disparity between this and the used count.",
            },
        },
        "memory_mb_used": {
            "type": "integer",
            "x-openstack": {
                "max-ver": "2.87",
                "description": "The memory used in this hypervisor (in MiB).",
            },
        },
        "running_vms": {
            "type": "integer",
            "x-openstack": {
                "max-ver": "2.87",
                "description": "The number of running VMs on this hypervisor. ",
            },
        },
        "service": {
            "type": "object",
            "description": "The hypervisor service object.",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "The name of the host.",
                },
                "id": {
                    "type": ["integer", "string"],
                    "format": "uuid",
                    "description": "The id of the service.",
                },
                "disabled_reason": {
                    "type": ["string", "null"],
                    "description": "The disable reason of the service, null if the service is enabled or disabled without reason provided.",
                },
            },
        },
        "uptime": {
            "type": "string",
            "description": "The total uptime of the hypervisor and information about average load. Only reported for active hosts where the virt driver supports this feature.",
            "x-openstack": {"min-ver": "2.87"},
        },
        "vcpus": {
            "type": "integer",
            "x-openstack": {"max-ver": "2.87"},
            "description": "The number of vCPU in this hypervisor. This does not take allocation ratios used for overcommit into account so there may be disparity between this and the used count.",
        },
        "vcpus_used": {
            "type": "integer",
            "x-openstack": {"max-ver": "2.87"},
            "description": "The number of vCPU used in this hypervisor.",
        },
        **HYPERVISOR_SHORT_SCHEMA["properties"],
    },
}

HYPERVISOR_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"hypervisor": copy.deepcopy(HYPERVISOR_SCHEMA)},
}


HYPERVISOR_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "hypervisors": {
            "type": "array",
            "description": "An array of hypervisor information.",
            "items": copy.deepcopy(HYPERVISOR_SHORT_SCHEMA),
        },
        "hypervisor_links": LINKS_SCHEMA,
    },
}

HYPERVISOR_LIST_DETAIL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "hypervisors": {
            "type": "array",
            "description": "An array of hypervisor information.",
            "items": copy.deepcopy(HYPERVISOR_SCHEMA),
        },
        "hypervisor_links": LINKS_SCHEMA,
    },
}

INSTANCE_USAGE_AUDIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "The object of instance usage audit log information.",
    "properties": {
        "hosts_not_run": {
            "type": "array",
            "items": {"type": "string"},
            "description": "A list of the hosts whose instance audit tasks have not run.",
        },
        "log": {
            "type": "object",
            "description": "The object of instance usage audit logs.",
        },
        "errors": {"type": "integer", "description": "The number of errors."},
        "instances": {
            "type": "integer",
            "description": "The number of instances.",
        },
        "message": {
            "type": "string",
            "description": "The log message of the instance usage audit task.",
        },
        "state": {
            "type": "string",
            "enum": ["DONE", "RUNNING"],
            "description": "The state of the instance usage audit task. DONE or RUNNING.",
        },
        "num_hosts": {
            "type": "integer",
            "description": "The number of the hosts.",
        },
        "num_hosts_done": {
            "type": "integer",
            "description": "The number of the hosts whose instance audit tasks have been done.",
        },
        "num_hosts_not_run": {
            "type": "integer",
            "description": "The number of the hosts whose instance audit tasks have not run.",
        },
        "num_hosts_running": {
            "type": "integer",
            "description": "The number of the hosts whose instance audit tasks are running.",
        },
        "overall_status": {
            "type": "string",
            "description": (
                "The overall status of instance audit tasks."
                "M of N hosts done. K errors."
                "The M value is the number of hosts whose instance audit tasks have been done in the period. The N value is the number of all hosts. The K value is the number of hosts whose instance audit tasks cause errors. If instance audit tasks have been done at all hosts in the period, the overall status is as follows:"
                "ALL hosts done. K errors."
            ),
        },
        "period_beginning": {
            "type": "string",
            "format": "date-time",
            "description": "The beginning time of the instance usage audit period. For example, 2016-05-01 00:00:00.",
        },
        "period_ending": {
            "type": "string",
            "format": "date-time",
            "description": "The ending time of the instance usage audit period. For example, 2016-06-01 00:00:00.",
        },
        "total_errors": {
            "type": "integer",
            "description": "The total number of instance audit task errors.",
        },
        "total_instances": {
            "type": "integer",
            "description": "The total number of VM instances in the period.",
        },
    },
}


KEYPAIR_SHORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Keypair object",
    "properties": {
        "name": {"type": "string", "description": "The name for the keypair"},
        "public_key": {
            "type": "string",
            "description": "The keypair public key.",
        },
        "fingerprint": {
            "type": "string",
            "description": "The fingerprint for the keypair.",
        },
        "type": {
            "type": "string",
            "description": "The type of the keypair. Allowed values are ssh or x509.",
            "x-openstack": {"min-ver": "2.2"},
        },
    },
}

KEYPAIR_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "keypairs": {
            "type": "array",
            "description": "Array of Keypair objects",
            "items": {
                "type": "object",
                "properties": {
                    "keypair": copy.deepcopy(KEYPAIR_SHORT_SCHEMA),
                },
            },
        },
        "keypairs_links": copy.deepcopy(LINKS_SCHEMA),
    },
}

KEYPAIR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Keypair object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "The user_id for a keypair.",
        },
        "deleted": {
            "type": "boolean",
            "description": "A boolean indicates whether this keypair is deleted or not. The value is always false (not deleted).",
        },
        "created_at": {
            "type": "string",
            "format": "date-time",
            "description": "The date and time when the resource was created.",
        },
        "deleted_at": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "It is always null.",
        },
        "updated_at": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "It is always null.",
        },
        "id": {"type": "integer", "description": "The keypair ID."},
        **copy.deepcopy(KEYPAIR_SHORT_SCHEMA["properties"]),
    },
}

KEYPAIR_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Keypair object",
    "properties": {"keypair": KEYPAIR_SCHEMA},
}

KEYPAIR_CREATED_SCHEMA: dict[str, Any] = copy.deepcopy(
    KEYPAIR_CONTAINER_SCHEMA
)
KEYPAIR_CREATED_SCHEMA["properties"]["keypair"]["properties"][
    "private_key"
] = {
    "type": "string",
    "description": "If you do not provide a public key on create, a new keypair will be built for you, and the private key will be returned during the initial create call. Make sure to save this, as there is no way to get this private key again in the future.",
    "x-openstack": {"max-ver": "2.91"},
}

MIGRATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Migration object",
    "properties": {
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
        "dest_compute": {
            "type": "string",
            "description": "The target compute for a migration.",
        },
        "dest_host": {
            "type": "string",
            "description": "The target host for a migration.",
        },
        "dest_node": {
            "type": "string",
            "description": "The target node for a migration.",
        },
        "id": {
            "type": "integer",
            "description": "The ID of the server migration.",
        },
        "instance_uuid": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the server.",
        },
        "new_instance_type_id": {
            "type": "integer",
            "description": "In resize case, the flavor ID for resizing the server. In the other cases, this parameter is same as the flavor ID of the server when the migration was started.",
        },
        "old_instance_type_id": {
            "type": "integer",
            "description": "The flavor ID of the server when the migration was started.",
        },
        "source_compute": {
            "type": "string",
            "description": "The source compute for a migration.",
        },
        "source_node": {
            "type": "string",
            "description": "The source node for a migration.",
        },
        "status": {
            "type": "string",
            "description": "The current status of the migration.",
        },
        "project_id": {
            "type": ["string", "null"],
            "description": "The ID of the project which initiated the server migration. The value may be null for older migration records.",
            "x-openstack": {"min-ver": "2.80"},
        },
        "user_id": {
            "type": ["string", "null"],
            "description": "The ID of the user which initiated the server migration. The value may be null for older migration records.",
            "x-openstack": {"min-ver": "2.80"},
        },
        "migration_type": {
            "type": "string",
            "enum": ["live-migration", "migration", "resize"],
            "description": "The type of the server migration. This is one of live-migration, migration, resize and evacuation. New in version 2.23",
            "x-openstack": {"min-ver": "2.23"},
        },
        "uuid": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the migration.",
            "x-openstack": {"min-ver": "2.59"},
        },
    },
}

MIGRATION_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "List of migration objects",
    "properties": {
        "migrations": {
            "type": "array",
            "items": copy.deepcopy(MIGRATION_SCHEMA),
        },
        "migrations_links": {
            "x-openstack": {"min-ver": "2.59"},
            **copy.deepcopy(LINKS_SCHEMA),
        },
    },
}

SERVER_MIGRATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Migration object",
    "properties": {
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
        "dest_compute": {
            "type": "string",
            "description": "The target compute for a migration.",
        },
        "dest_host": {
            "type": "string",
            "description": "The target host for a migration.",
        },
        "dest_node": {
            "type": "string",
            "description": "The target node for a migration.",
        },
        "id": {
            "type": "integer",
            "description": "The ID of the server migration.",
        },
        "source_compute": {
            "type": "string",
            "description": "The source compute for a migration.",
        },
        "source_node": {
            "type": "string",
            "description": "The source node for a migration.",
        },
        "status": {
            "type": "string",
            "description": "The current status of the migration.",
        },
        "project_id": {
            "type": ["string", "null"],
            "description": "The ID of the project which initiated the server migration. The value may be null for older migration records.",
            "x-openstack": {"min-ver": "2.80"},
        },
        "user_id": {
            "type": ["string", "null"],
            "description": "The ID of the user which initiated the server migration. The value may be null for older migration records.",
            "x-openstack": {"min-ver": "2.80"},
        },
        "uuid": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the migration.",
            "x-openstack": {"min-ver": "2.59"},
        },
        "disk_processed_bytes": {
            "type": "integer",
            "description": "The amount of disk, in bytes, that has been processed during the migration.",
        },
        "disk_remaining_bytes": {
            "type": "integer",
            "description": "The amount of disk, in bytes, that still needs to be migrated.",
        },
        "disk_total_bytes": {
            "type": "integer",
            "description": "The total amount of disk, in bytes, that needs to be migrated.",
        },
        "memory_processed_bytes": {
            "type": "integer",
            "description": "The amount of memory, in bytes, that has been processed during the migration.",
        },
        "memory_remaining_bytes": {
            "type": "integer",
            "description": "The amount of memory, in bytes, that still needs to be migrated.",
        },
        "memory_total_bytes": {
            "type": "integer",
            "description": "The total amount of memory, in bytes, that needs to be migrated.",
        },
        "server_uuid": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the server.",
        },
    },
}
SERVER_MIGRATION_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "List of migration objects",
    "properties": {
        "migrations": {
            "type": "array",
            "items": copy.deepcopy(SERVER_MIGRATION_SCHEMA),
        },
    },
}
SERVER_MIGRATION_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"migration": copy.deepcopy(SERVER_MIGRATION_SCHEMA)},
}

QUOTA_SET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Quota Set object",
    "properties": {
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the tenant/user the quotas listed for.",
        },
        **quota_sets.quota_resources,
    },
}

QUOTA_SET_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"quota_set": QUOTA_SET_SCHEMA},
}
QUOTA_DETAIL_SCHEMA: dict[str, Any] = {
    "in_use": {"type": "integer"},
    "limit": {"type": "integer"},
    "reserved": {"type": "integer"},
}
QUOTA_SET_DETAIL_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "quota_set": {
            "type": "object",
            "description": "A quota_set object.",
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "The UUID of the tenant/user the quotas listed for.",
                },
                "instances": {
                    "type": "object",
                    "description": "The object of detailed servers quota, including in_use, limit and reserved number of instances.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                },
                "cores": {
                    "type": "object",
                    "description": "The object of detailed key pairs quota, including in_use, limit and reserved number of key pairs.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                },
                "ram": {
                    "type": "object",
                    "description": "The object of detailed key ram quota, including in_use, limit and reserved number of ram.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                },
                "floating_ips": {
                    "type": "object",
                    "description": "The object of detailed floating ips quota, including in_use, limit and reserved number of floating ips.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                    "x-openstack": {"max-ver": "2.35"},
                },
                "fixed_ips": {
                    "type": "object",
                    "description": "The object of detailed fixed ips quota, including in_use, limit and reserved number of fixed ips.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                    "x-openstack": {"max-ver": "2.35"},
                },
                "metadata_items": {
                    "type": "object",
                    "description": "The object of detailed key metadata items quota, including in_use, limit and reserved number of metadata items.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                },
                "key_pairs": {
                    "type": "object",
                    "description": "The object of detailed key pairs quota, including in_use, limit and reserved number of key pairs.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                },
                "security_groups": {
                    "type": "object",
                    "description": "The object of detailed security groups, including in_use, limit and reserved number of security groups.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                    "x-openstack": {"max-ver": "2.35"},
                },
                "security_group_rules": {
                    "type": "object",
                    "description": "The object of detailed security group rules quota, including in_use, limit and reserved number of security group rules.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                    "x-openstack": {"max-ver": "2.35"},
                },
                "injected_files": {
                    "type": "object",
                    "description": "The object of detailed injected files quota, including in_use, limit and reserved number of injected files.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                    "x-openstack": {"max-ver": "2.56"},
                },
                "injected_files_content_bytes": {
                    "type": "object",
                    "description": "The object of detailed injected file content bytes quota, including in_use, limit and reserved number of injected file content bytes.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                    "x-openstack": {"max-ver": "2.56"},
                },
                "injected_files_path_bytes": {
                    "type": "object",
                    "description": "The object of detailed injected file path bytes quota, including in_use, limit and reserved number of injected file path bytes.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                    "x-openstack": {"max-ver": "2.56"},
                },
                "server_groups": {
                    "type": "object",
                    "description": "The object of detailed server groups, including in_use, limit and reserved number of server groups.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                },
                "server_group_members": {
                    "type": "object",
                    "description": "The object of detailed server group members, including in_use, limit and reserved number of server group members.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                },
                "networks": {
                    "type": "object",
                    "description": "The number of private networks that can be created per project.",
                    "properties": QUOTA_DETAIL_SCHEMA,
                    "x-openstack": {"max-ver": "2.35"},
                },
            },
        }
    },
}
# TODO(gtema): class set props are not quota_set props, but for now keep this way
QUOTA_CLASS_SET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Quota Class Set object",
    "properties": {
        "id": {
            "type": "string",
            "description": "The ID of the quota class. Nova supports the default Quota Class only.",
        },
        **quota_sets.quota_resources,
    },
}

QUOTA_CLASS_SET_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"quota_class_set": QUOTA_CLASS_SET_SCHEMA},
}

EXTERNAL_EVENTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "events": {
            "description": "List of external events to process.",
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "enum": [
                            "network-changed",
                            "network-vif-plugged",
                            "network-vif-unplugged",
                            "network-vif-deleted",
                            "volume-extended",
                            "power-update",
                            "accelerator-request-bound",
                        ],
                        "description": "The event name.",
                    },
                    "server_uuid": {
                        "type": "string",
                        "format": "uuid",
                        "description": "The UUID of the server instance to which the API dispatches the event. You must assign this instance to a host. Otherwise, this call does not dispatch the event to the instance.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["failed", "completed", "in-progress"],
                        "description": "The event status. Default is `completed`.",
                    },
                    "tag": {
                        "type": "string",
                        "description": "A string value that identifies the event.",
                    },
                },
            },
        }
    },
}

SERVER_GROUP_POLICIES = [
    "anti-affinity",
    "affinity",
    "soft-anti-affinity",
    "soft-affinity",
]

SERVER_GROUP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the server group.",
            "readOnly": True,
        },
        "members": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The list of members in the server group",
        },
        "metadata": {
            "description": "Metadata key and value pairs. The maximum size for each metadata key and value pair is 255 bytes. It’s always empty and only used for keeping compatibility.",
            "x-openstack": {"max-ver": "2.63"},
            **parameter_types.metadata,
        },
        "name": {
            "type": "string",
            "description": "A name identifying the server group",
        },
        "policies": {
            "type": "array",
            "items": {"type": "string", "enum": SERVER_GROUP_POLICIES},
            "description": "A list of exactly one policy name to associate with the server group.",
            "maxItems": 1,
            "x-openstack": {"max-ver": "2.63"},
        },
        "policy": {
            "type": "string",
            "description": "The policy field represents the name of the policy",
            "enum": SERVER_GROUP_POLICIES,
            "x-openstack": {"min-ver": "2.64"},
        },
        "project_id": {
            "type": "string",
            "description": "The project ID who owns the server group.",
            "x-openstack": {"min-ver": "2.13"},
        },
        "rules": {
            "type": "object",
            "description": "The rules field, which is a dict, can be applied to the policy. Currently, only the max_server_per_host rule is supported for the anti-affinity policy. The max_server_per_host rule allows specifying how many members of the anti-affinity group can reside on the same compute host. If not specified, only one member from the same anti-affinity group can reside on a given host.",
            "properties": {
                "max_server_per_host": parameter_types.positive_integer,
            },
            "additionalProperties": False,
            "x-openstack": {"min-ver": "2.64"},
        },
        "user_id": {
            "type": "string",
            "description": "The user ID who owns the server group",
            "x-openstack": {"min-ver": "2.13"},
        },
    },
}

SERVER_GROUP_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "server_groups": {
            "description": "The list of existing server groups.",
            "type": "array",
            "items": SERVER_GROUP_SCHEMA,
        }
    },
}
SERVER_GROUP_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"server_group": SERVER_GROUP_SCHEMA},
}

SERVICE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "zone": {
            "type": "string",
            "description": "The availability zone of service",
            "x-openstack-sdk-name": "availability_zone",
        },
        "binary": {"type": "string", "description": "Binary name of service"},
        "disabled_reason": {
            "type": "string",
            "description": "Disabled reason of service",
        },
        "host": {
            "type": "string",
            "description": "The name of the host where service runs",
        },
        "id": {
            "type": ["integer", "string"],
            "format": "uuid",
            "description": "Id of the resource",
            "readOnly": True,
        },
        "forced_down": {
            "type": "boolean",
            "description": "Whether or not this service was forced down manually by an administrator after the service was fenced",
            "x-openstack": {"min-ver": "2.11"},
        },
        "name": {"type": "string", "description": "Service name"},
        "state": {"type": "string", "description": "State of service"},
        "status": {
            "type": "string",
            "description": "Status of service",
            "enum": ["disabled", "enabled"],
            "readOnly": True,
        },
        "updated_at": {
            "type": "string",
            "description": "The date and time when the resource was updated",
            "readOnly": True,
        },
    },
}

SERVICE_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"service": SERVICE_SCHEMA},
}

SERVICE_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "services": {
            "type": "array",
            "items": SERVICE_SCHEMA,
            "description": "A list of service objects.",
        }
    },
}

TENANT_USAGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tenant_id": {
            "type": "string",
            "description": "The UUID of the project in a multi-tenancy cloud.",
        },
        "start": {
            "type": "string",
            "format": "date-time",
            "description": "The beginning time to calculate usage statistics on compute and storage resources.",
        },
        "stop": {
            "type": "string",
            "format": "date-time",
            "description": "The ending time to calculate usage statistics on compute and storage resources.",
        },
        "total_hours": {
            "type": "number",
            "format": "float",
            "description": "The total duration that servers exist (in hours).",
        },
        "total_local_gb_usage": {
            "type": "number",
            "format": "float",
            "description": "Multiplying the server disk size (in GiB) by hours the server exists, and then adding that all together for each server.",
        },
        "total_memory_mb_usage": {
            "type": "number",
            "format": "float",
            "description": "Multiplying the server memory size (in MiB) by hours the server exists, and then adding that all together for each server.",
        },
        "total_vcpus_usage": {
            "type": "number",
            "format": "float",
            "description": "Multiplying the number of virtual CPUs of the server by hours the server exists, and then adding that all together for each server.",
        },
        "server_usages": {
            "type": "array",
            "description": "A list of the server usage objects.",
            "items": {
                "type": "object",
                "properties": {
                    "ended_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "The date and time when the server was deleted.",
                    },
                    "flavor": {
                        "type": "string",
                        "description": "The display name of a flavor.",
                    },
                    "hours": {
                        "type": "number",
                        "format": "float",
                        "description": "The duration that the server exists (in hours).",
                    },
                    "instance_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "The UUID of the server.",
                    },
                    "local_gb": {
                        "type": "integer",
                        "description": "The sum of the root disk size of the server and the ephemeral disk size of it (in GiB).",
                    },
                    "memory_mb": {
                        "type": "integer",
                        "description": "The memory size of the server (in MiB).",
                    },
                    "name": {
                        "type": "string",
                        "description": "The server name.",
                    },
                    "tenant_id": {
                        "type": "string",
                        "description": "The UUID of the project in a multi-tenancy cloud.",
                    },
                    "started_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "The date and time when the server was launched.",
                    },
                    "state": {
                        "type": "string",
                        "description": "The VM state.",
                    },
                    "uptime": {
                        "type": "integer",
                        "description": "The uptime of the server.",
                    },
                    "vcpus": {
                        "type": "integer",
                        "description": "The number of virtual CPUs that the server uses.",
                    },
                },
            },
        },
    },
}

TENANT_USAGE_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tenant_usages": {
            "type": "array",
            "items": TENANT_USAGE_SCHEMA,
            "description": "A list of the tenant usage objects.",
        },
        "tenant_usages_links": LINKS_SCHEMA,
    },
}

SERVER_SHORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Server object",
    "properties": {
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "Server ID.",
        },
        "name": {
            "type": "string",
            "format": "uuid",
            "description": "Server name.",
        },
    },
}
SERVER_ADDRESSES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "A dictionary of addresses this server can be accessed through. The dictionary contains keys such as ``private`` and ``public``, each containing a list of dictionaries for addresses of that type. The addresses are contained in a dictionary with keys ``addr`` and ``version``, which is either 4 or 6 depending on the protocol of the IP address.",
    "additionalProperties": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "addr": {
                    "description": "The IP address.",
                    **parameter_types.ip_address,
                },
                "version": {
                    "type": "integer",
                    "enum": [4, 6],
                    "description": "The IP version of the address associated with server.",
                },
            },
        },
    },
}
SERVER_ADDRESSES_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "The addresses information for the server.",
    "properties": {"addresses": SERVER_ADDRESSES_SCHEMA},
}


SERVER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Server object",
    "properties": {
        "accessIPv4": {
            "description": "IPv4 address that should be used to access this server. May be automatically set by the provider.",
            **parameter_types.ipv4,
        },
        "accessIPv6": {
            "description": "IPv6 address that should be used to access this server. May be automatically set by the provider.",
            **parameter_types.ipv6,
        },
        "addresses": SERVER_ADDRESSES_SCHEMA,
        "os-extended-volumes:volumes_attached": {
            "type": "array",
            "items": {"type": "object"},
            "description": "A list of an attached volumes. Each item in the list contains at least an 'id' key to identify the specific volumes.",
        },
        "OS-EXT-AZ:availability_zone": {
            "type": "string",
            "description": "The name of the availability zone this server is a part of.",
        },
        "OS-EXT-SRV-ATTR:host": {
            "type": "string",
            "description": "The name of the compute host on which this instance is running. Appears in the response for administrative users only.",
        },
        "config_drive": {
            "type": "string",
            "description": "Indicates whether a configuration drive enables metadata injection. Not all cloud providers enable this feature.",
        },
        "created": {
            "type": "string",
            "format": "date-time",
            "description": "Timestamp of when the server was created.",
            "readOnly": True,
        },
        "description": {
            "type": "string",
            "description": "The description of the server. Before microversion 2.19 this was set to the server name.",
        },
        "OS-DCF:diskConfig": {
            "type": "string",
            "description": "The disk configuration. Either AUTO or MANUAL.",
            "enum": ["AUTO", "MANUAL"],
        },
        "fault": {
            "type": "object",
            "description": "A fault object. Only available when the server status is ERROR or DELETED and a fault occurred.",
            "properties": {
                "code": {
                    "type": "integer",
                    "description": "The error response code.",
                },
                "created": {
                    "type": "string",
                    "format": "date-time",
                    "description": "The date and time when the exception was raised.",
                },
                "message": {
                    "type": "string",
                    "description": "The error message.",
                },
                "details": {
                    "type": "string",
                    "description": "The stack trace. It is available if the response code is not 500 or you have the administrator privilege",
                },
            },
            "additionalProperties": False,
        },
        "flavor": {
            "type": "object",
            "description": "The flavor property as returned from server.",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "The ID of the flavor. While people often make this look like an int, this is really a string.",
                    "x-openstack": {"max-ver": "2.46"},
                },
                "links": {
                    "description": "Links to the flavor resource",
                    "x-openstack": {"max-ver": "2.46"},
                    **LINKS_SCHEMA,
                },
                "vcpus": {
                    "type": "integer",
                    "description": "The number of virtual CPUs that were allocated to the server.",
                    "x-openstack": {"min-ver": "2.47"},
                },
                "ram": {
                    "type": "integer",
                    "description": "The amount of RAM a flavor has, in MiB.",
                    "x-openstack": {"min-ver": "2.47"},
                },
                "disk": {
                    "type": "integer",
                    "description": "The size of the root disk that was created in GiB.",
                    "x-openstack": {"min-ver": "2.47"},
                },
                "ephemeral": {
                    "type": "integer",
                    "description": "The size of the ephemeral disk that was created, in GiB.",
                    "x-openstack": {"min-ver": "2.47"},
                },
                "swap": {
                    "type": "integer",
                    "description": "The size of a dedicated swap disk that was allocated, in MiB.",
                    "x-openstack": {"min-ver": "2.47"},
                },
                "original_name": {
                    "type": "string",
                    "description": "The display name of a flavor.",
                    "x-openstack": {"min-ver": "2.47"},
                },
                "extra_specs": {
                    "description": "A dictionary of the flavor’s extra-specs key-and-value pairs. This will only be included if the user is allowed by policy to index flavor extra_specs.",
                    "x-openstack": {"min-ver": "2.47"},
                    **parameter_types.metadata,
                },
            },
        },
        "hostId": {
            "type": "string",
            "description": "An ID representing the host of this server.",
        },
        "host_status": {
            "type": ["string", "null"],
            "description": "The host status.",
            "enum": ["UP", "DOWN", "MAINTENANCE", "UNKNOWN", "", "null"],
            "x-openstack": {"min-ver": "2.16"},
        },
        "OS-EXT-SRV-ATTR:hostname": {
            "type": "string",
            "description": "The hostname set on the instance when it is booted. By default, it appears in the response for administrative users only.",
            "x-openstack": {"min-ver": "2.3"},
        },
        "OS-EXT-SRV-ATTR:hypervisor_hostname": {
            "type": "string",
            "description": "The hypervisor host name. Appears in the response for administrative users only.",
            "x-openstack-sdk-name": "hypervisor_hostname",
        },
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "Id of the server",
            "readOnly": True,
        },
        "image": {
            "type": "object",
            "description": "The image property as returned from server.",
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "The image ID",
                },
                "links": {"description": "Image links", **LINKS_SCHEMA},
            },
        },
        "OS-EXT-SRV-ATTR:instance_name": {
            "type": "string",
            "description": "The instance name. The Compute API generates the instance name from the instance name template. Appears in the response for administrative users only.",
        },
        "locked": {
            "type": "boolean",
            "description": "True if the instance is locked otherwise False.",
            "x-openstack": {"min-ver": "2.9"},
        },
        "OS-EXT-SRV-ATTR:kernel_id": {
            "type": "string",
            "description": "The UUID of the kernel image when using an AMI. Will be null if not. By default, it appears in the response for administrative users only.",
            "x-openstack": {"min-ver": "2.3"},
        },
        "key_name": {
            "type": "string",
            "description": "The name of an associated keypair",
        },
        "OS-EXT-SRV-ATTR:launch_index": {
            "type": "integer",
            "description": "When servers are launched via multiple create, this is the sequence in which the servers were launched. By default, it appears in the response for administrative users only.",
            "x-openstack": {"min-ver": "2.3"},
        },
        "OS-SRV-USG:launched_at": {
            "type": "string",
            "description": "The timestamp when the server was launched.",
        },
        "links": {
            "description": "A list of dictionaries holding links relevant to this server.",
            **LINKS_SCHEMA,
        },
        "metadata": {
            "type": "object",
            "description": "A dictionary of metadata key-and-value pairs, which is maintained for backward compatibility.",
            **parameter_types.metadata,
        },
        "name": {"type": "string", "description": "Name"},
        "OS-EXT-STS:power_state": {
            "type": "integer",
            "description": (
                "The power state of this server. This is an enum value that is mapped as:\n"
                " - 0: NOSTATE\n"
                " - 1: RUNNING\n"
                " - 3: PAUSED\n"
                " - 4: SHUTDOWN\n"
                " - 6: CRASHED\n"
                " - 7: SUSPENDED\n"
            ),
        },
        "progress": {
            "type": "integer",
            "description": "While the server is building, this value represents the percentage of completion. Once it is completed, it will be 100.",
        },
        "tenant_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the project this server is associated with.",
        },
        "OS-EXT-SRV-ATTR:ramdisk_id": {
            "type": "string",
            "description": "The UUID of the ramdisk image when using an AMI. Will be null if not. By default, it appears in the response for administrative users only.",
            "x-openstack": {"min-ver": "2.3"},
        },
        "OS-EXT-SRV-ATTR:reservation_id": {
            "type": "string",
            "description": "The reservation id for the server. This is an id that can be useful in tracking groups of servers created with multiple create, that will all have the same reservation_id. By default, it appears in the response for administrative users only.",
            "x-openstack": {"min-ver": "2.3"},
        },
        "OS-EXT-SRV-ATTR:root_device_name": {
            "type": "string",
            "description": "The root device name for the instance By default, it appears in the response for administrative users only.",
            "x-openstack": {"min-ver": "2.3"},
        },
        "security_groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The security group name",
                    }
                },
            },
            "description": "One or more security groups objects.",
        },
        "server_groups": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The UUIDs of the server groups to which the server belongs. Currently this can contain at most one entry.",
            "x-openstack": {"min-ver": "2.71"},
        },
        "status": {
            "type": "string",
            "description": "The state this server is in. Valid values include ``ACTIVE``, ``BUILDING``, ``DELETED``, ``ERROR``, ``HARD_REBOOT``, ``PASSWORD``, ``PAUSED``, ``REBOOT``, ``REBUILD``, ``RESCUED``, ``RESIZED``, ``REVERT_RESIZE``, ``SHUTOFF``, ``SOFT_DELETED``, ``STOPPED``, ``SUSPENDED``, ``UNKNOWN``, or ``VERIFY_RESIZE``.",
            "readOnly": True,
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "A list of tags. The maximum count of tags in this list is 50.",
            "x-openstack": {"min-ver": "2.26"},
        },
        "OS-EXT-STS:task_state": {
            "type": "string",
            "description": "The task state of this server.",
        },
        "OS-SRV-USG:terminated_at": {
            "type": "string",
            "description": "The timestamp when the server was terminated (if it has been).",
        },
        "trusted_image_certificates": {
            "type": ["array", "null"],
            "items": {"type": "string"},
            "description": "A list of trusted certificate IDs, that were used during image signature verification to verify the signing certificate. The list is restricted to a maximum of 50 IDs. The value is null if trusted certificate IDs are not set.",
            "x-openstack": {"min-ver": "2.63"},
        },
        "updated": {
            "type": "string",
            "format": "date-time",
            "description": "Timestamp of when this server was last updated.",
            "readOnly": True,
        },
        "OS-EXT-SRV-ATTR:user_data": {
            "type": "string",
            "description": "Configuration information or scripts to use upon launch. Must be Base64 encoded.",
            "x-openstack": {"min-ver": "2.3"},
        },
        "user_id": {
            "type": "string",
            "description": "The ID of the owners of this server.",
        },
        "OS-EXT-STS:vm_state": {
            "type": "string",
            "description": "The VM state of this server.",
        },
    },
}

SERVER_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"server": copy.deepcopy(SERVER_SCHEMA)},
}

SERVER_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "servers": {
            "type": "array",
            "items": copy.deepcopy(SERVER_SHORT_SCHEMA),
        },
        "servers_links": LINKS_SCHEMA,
    },
}

SERVER_LIST_DETAIL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "servers": {"type": "array", "items": copy.deepcopy(SERVER_SCHEMA)},
        "servers_links": LINKS_SCHEMA,
    },
}
SERVER_CREATED_SCHEMA: dict[str, Any] = {
    "oneOf": [
        {
            "type": "object",
            "description": "Created server object",
            "properties": {
                "server": {
                    "type": "object",
                    "properties": {
                        "OS-DCF:diskConfig": {
                            "type": "string",
                            "description": "The disk configuration. Either AUTO or MANUAL.",
                            "enum": ["AUTO", "MANUAL"],
                        },
                        "adminPass": {
                            "type": "string",
                            "format": "password",
                            "description": "The administrative password for the server. If you set enable_instance_password configuration option to False, the API wouldn’t return the adminPass field in response.",
                        },
                        "id": {
                            "type": "string",
                            "format": "uuid",
                            "description": "Id of the server",
                            "readOnly": True,
                        },
                        "security_groups": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "The security group name",
                                    }
                                },
                            },
                            "description": "One or more security groups objects.",
                        },
                        "links": LINKS_SCHEMA,
                    },
                }
            },
        },
        {
            "type": "object",
            "properties": {
                "reservation_id": {
                    "type": "string",
                    "description": "The reservation id for the server. This is an id that can be useful in tracking groups of servers created with multiple create, that will all have the same reservation_id.",
                }
            },
        },
    ]
}

SERVER_ACTION_CREATE_IMAGE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "image_id": {
            "type": "string",
            "description": "The UUID for the resulting image snapshot.",
            "x-openstack": {"min-ver": "2.45"},
        }
    },
}
SERVER_ACTION_NEW_ADMINPASS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "adminPass": {
            "type": "string",
            "description": "An administrative password to access moved instance. If you set enable_instance_password configuration option to False, the API wouldn’t return the adminPass field in response.",
        }
    },
}
SERVER_ACTION_GET_CONSOLE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "The console output as a string. Control characters will be escaped to create a valid JSON string.",
    "properties": {"output": {"type": "string"}},
}
SERVER_ACTION_REMOTE_CONSOLE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "The remote console object.",
    "properties": {
        "console": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "description": "The type of the remote console",
                    "enum": ["rdp-html5", "serial", "spice-html5", "novnc"],
                },
                "url": {
                    "type": "string",
                    "description": "The URL used to connect to the console.",
                },
            },
        }
    },
}
SERVER_DIAGNOSTICS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cpu_details": {
            "type": "array",
            "items": {"type": "object"},
            "description": "The list of dictionaries with detailed information about VM CPUs.",
            "x-openstack": {"min-ver": "2.48"},
        },
        "disk_details": {
            "type": "array",
            "items": {"type": "object"},
            "description": "The list of dictionaries with detailed information about VM disks.",
            "x-openstack": {"min-ver": "2.48"},
        },
        "driver": {
            "type": "string",
            "description": "The driver on which the VM is running.",
            "enum": ["libvirt", "xenapi", "hyperv", "vmwareapi", "ironic"],
            "x-openstack": {"min-ver": "2.48"},
        },
        "config_drive": {
            "type": "boolean",
            "description": "Indicates whether or not a config drive was used for this server.",
            "x-openstack": {"min-ver": "2.48"},
        },
        "hypervisor": {
            "type": "string",
            "description": "The hypervisor on which the VM is running.",
            "x-openstack": {"min-ver": "2.48"},
        },
        "hypervisor_os": {
            "type": "string",
            "description": "The hypervisor OS.",
            "x-openstack": {"min-ver": "2.48"},
        },
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "Id of the resource",
            "readOnly": True,
        },
        "memory_details": {
            "type": "array",
            "items": {"type": "object"},
            "description": "The dictionary with information about VM memory usage.",
            "x-openstack": {"min-ver": "2.48"},
        },
        "name": {"type": "string", "description": "Name"},
        "nic_details": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "mac_address": {"type": "string", "description": ""},
                    "rx_octets": {"type": "integer", "description": ""},
                    "rx_errors": {"type": "integer", "description": ""},
                    "rx_drop": {"type": "integer", "description": ""},
                    "rx_packets": {"type": "integer", "description": ""},
                    "rx_rate": {"type": "integer", "description": ""},
                    "tx_octets": {"type": "integer", "description": ""},
                    "tx_errors": {"type": "integer", "description": ""},
                    "tx_drop": {"type": "integer", "description": ""},
                    "tx_packets": {"type": "integer", "description": ""},
                    "tx_rate": {"type": "integer", "description": ""},
                },
            },
            "description": "The list of dictionaries with detailed information about VM NICs.",
            "x-openstack": {"min-ver": "2.48"},
        },
        "num_cpus": {
            "type": "integer",
            "description": "The number of vCPUs.",
            "x-openstack": {"min-ver": "2.48"},
        },
        "num_disks": {
            "type": "integer",
            "description": "The number of disks.",
            "x-openstack": {"min-ver": "2.48"},
        },
        "num_nics": {
            "type": "integer",
            "description": "The number of vNICs.",
            "x-openstack": {"min-ver": "2.48"},
        },
        "state": {
            "type": "string",
            "description": "The current state of the VM.",
            "enum": [
                "pending",
                "running",
                "paused",
                "shutdown",
                "crashed",
                "suspended",
            ],
            "x-openstack": {"min-ver": "2.48"},
        },
        "uptime": {
            "type": "integer",
            "description": "The amount of time in seconds that the VM has been running.",
            "x-openstack": {"min-ver": "2.48"},
        },
    },
}

SERVER_METADATA_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Metadata key and value pairs. The maximum size for each metadata key and value pair is 255 bytes.",
    "properties": {"metadata": parameter_types.metadata},
}
SERVER_METADATA_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Metadata key and value pairs. The maximum size for each metadata key and value pair is 255 bytes.",
    "properties": {"meta": {"maxProperties": 1, **parameter_types.metadata}},
}

SERVER_INSTANCE_ACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "The instance action object.",
    "properties": {
        "action": {"type": "string", "description": "The name of the action."},
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "event": {
                        "type": "string",
                        "description": "The name of the event.",
                    },
                    "start_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "The date and time when the event was started.",
                    },
                    "finish_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "The date and time when the event was finished.",
                    },
                    "result": {
                        "type": "string",
                        "description": "The result of the event.",
                    },
                    "traceback": {
                        "type": ["string", "null"],
                        "description": "he traceback stack if an error occurred in this event. Policy defaults enable only users with the administrative role to see an instance action event traceback. Cloud providers can change these permissions through the policy.json file.",
                    },
                    "hostId": {
                        "type": "string",
                        "description": "An obfuscated hashed host ID string, or the empty string if there is no host for the event. This is a hashed value so will not actually look like a hostname, and is hashed with data from the project_id, so the same physical host as seen by two different project_ids will be different. This is useful when within the same project you need to determine if two events occurred on the same or different physical hosts.",
                        "x-openstack": {"min-ver": "2.62"},
                    },
                    "host": {
                        "type": "string",
                        "description": "The name of the host on which the event occurred. Policy defaults enable only users with the administrative role to see an instance action event host. Cloud providers can change these permissions through the policy.json file.",
                        "x-openstack": {"min-ver": "2.62"},
                    },
                    "details": {
                        "type": ["string", "null"],
                        "description": "Details of the event. May be null.",
                        "x-openstack": {"min-ver": "2.84"},
                    },
                },
            },
            "description": "Events",
        },
        "message": {
            "type": ["string", "null"],
            "description": "The related error message for when an action fails.",
        },
        "project_id": {
            "type": "string",
            "description": "The ID of the project that this server belongs to.",
        },
        "request_id": {
            "type": "string",
            "description": "The ID of the request that this action related to.",
        },
        "start_time": {
            "type": "string",
            "format": "date-time",
            "description": "The date and time when the action was started.",
        },
        "user_id": {
            "type": "string",
            "description": "The ID of the user which initiated the server action.",
        },
        "updated_at": {
            "type": "string",
            "format": "date-time",
            "description": "The date and time when the instance action or the action event of instance action was updated.",
            "x-openstack": {"min-ver": "2.58"},
        },
    },
}
SERVER_INSTANCE_ACTION_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"instanceAction": SERVER_INSTANCE_ACTION_SCHEMA},
}
SERVER_INSTANCE_ACTION_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "instanceActions": {
            "type": "array",
            "items": SERVER_INSTANCE_ACTION_SCHEMA,
            "description": "List of the actions for the given instance in descending order of creation.",
        },
        "links": LINKS_SCHEMA,
    },
}

INTERFACE_ATTACHMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "The interface attachment.",
    "properties": {
        "fixed_ips": {
            "type": "array",
            "description": "Fixed IP addresses with subnet IDs.",
            "items": {
                "type": "object",
                "properties": {
                    "ip_address": {
                        "description": "The IP address.",
                        **parameter_types.ip_address,
                    },
                    "subnet_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "The UUID of the subnet.",
                    },
                },
            },
        },
        "mac_addr": {
            "description": "The MAC address",
            **parameter_types.mac_address,
        },
        "net_id": {
            "type": "string",
            "format": "uuid",
            "description": "The network ID.",
        },
        "port_id": {
            "type": "string",
            "format": "uuid",
            "description": "The port ID.",
        },
        "port_state": {"type": "string", "description": "The port state."},
        "tag": {
            "type": ["string", "null"],
            "description": "The device tag applied to the virtual network interface or null.",
            "x-openstack": {"min-ver": "2.70"},
        },
    },
}
INTERFACE_ATTACHMENT_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"interfaceAttachment": INTERFACE_ATTACHMENT_SCHEMA},
}
INTERFACE_ATTACHMENT_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "interfaceAttachments": {
            "type": "array",
            "items": INTERFACE_ATTACHMENT_SCHEMA,
        }
    },
}

SERVER_PASSWORD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "password": {
            "type": "string",
            "format": "password",
            "description": "The password returned from metadata server.",
        }
    },
}
SERVER_SECURITY_GROUPS_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "security_groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "The ID of the security group.",
                    },
                    "name": {
                        "type": "string",
                        "description": "The security group name.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Security group description.",
                    },
                    "tenant_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "The UUID of the tenant in a multi-tenancy cloud.",
                    },
                    "rules": {
                        "type": "array",
                        "description": "The list of security group rules.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "format": "uuid"},
                                "from_port": {"type": "integer"},
                                "to_port": {"type": "integer"},
                                "ip_protocol": {"type": "string"},
                                "ip_range": {"type": "object"},
                                "group": {
                                    "type": "object",
                                    "properties": {"name": {"type": "string"}},
                                },
                                "parent_group_id": {
                                    "type": "string",
                                    "format": "uuid",
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}


VOLUME_ATTACHMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "device": {
            "type": "string",
            "description": "Name of the device in the attachment object, such as, /dev/vdb.",
        },
        "id": {
            "description": "The volume ID of the attachment",
            "type": "string",
            "format": "uuid",
            "x-openstack": {"max-ver": "2.88"},
        },
        "serverId": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the server.",
        },
        "volumeId": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the attached volume.",
        },
        "tag": {
            "type": ["string", "null"],
            "description": "The device tag applied to the volume block device or null.",
            "x-openstack": {"min-ver": "2.70"},
        },
        "delete_on_termination": {
            "type": "boolean",
            "description": "A flag indicating if the attached volume will be deleted when the server is deleted.",
            "x-openstack": {"min-ver": "2.79"},
        },
        "attachment_id": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the associated volume attachment in Cinder.",
            "x-openstack": {"min-ver": "2.89"},
        },
        "bdm_uuid": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the block device mapping record in Nova for the attachment.",
            "x-openstack": {"min-ver": "2.89"},
        },
    },
}
VOLUME_ATTACHMENT_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"volumeAttachment": VOLUME_ATTACHMENT_SCHEMA},
}

VOLUME_ATTACHMENT_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "volumeAttachments": {
            "type": "array",
            "items": VOLUME_ATTACHMENT_SCHEMA,
        }
    },
}

EXTENSION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "An extension object.",
    "properties": {
        "alias": {
            "type": "string",
            "description": "A short name by which this extension is also known.",
        },
        "description": {
            "type": "string",
            "description": "Text describing this extension’s purpose.",
        },
        "links": copy.deepcopy(LINKS_SCHEMA),
        "name": {"type": "string", "description": "Name of the extension."},
        "namespace": {
            "type": "string",
            "description": "A URL pointing to the namespace for this extension.",
        },
        "updated": {
            "type": "string",
            "format": "date-time",
            "description": "The date and time when the resource was updated.",
        },
    },
}

EXTENSION_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "An extension object.",
    "properties": {"extension": copy.deepcopy(EXTENSION_SCHEMA)},
}

EXTENSION_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "An extension object.",
    "properties": {
        "extensions": {
            "type": "array",
            "items": copy.deepcopy(EXTENSION_SCHEMA),
        }
    },
}
