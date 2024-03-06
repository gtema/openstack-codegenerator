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
    TypeSchema,
    ParameterSchema,
    HeaderSchema,
)
from codegenerator.openapi.base import OpenStackServerSourceBase
from codegenerator.openapi import nova_schemas
from codegenerator.openapi.utils import merge_api_ref_doc


class NovaGenerator(OpenStackServerSourceBase):
    URL_TAG_MAP = {
        "/versions": "version",
        "/os-quota-sets": "quota-sets-os-quota-sets",
        "/os-quota-class-sets": "quota-class-sets-os-quota-class-sets",
        "/os-console-auth-tokens/": "server-consoles",
        "/servers/{server_id}/remote-consoles": "server-consoles",
        "/servers/{server_id}/migrations": "server-migrations",
        "/servers/{server_id}/tags": "server-tags",
    }

    def _api_ver_major(self, ver):
        return ver.ver_major

    def _api_ver_minor(self, ver):
        return ver.ver_minor

    def _api_ver(self, ver):
        return (ver.ver_major, ver.ver_minor)

    def _generate(self, target_dir, args):
        from nova.api.openstack import api_version_request
        from nova.api.openstack.compute import routes
        from nova.tests import fixtures as nova_fixtures

        self.api_version = api_version_request._MAX_API_VERSION
        self.min_api_version = api_version_request._MIN_API_VERSION

        self.useFixture(nova_fixtures.RPCFixture("nova.test"))
        self.router = routes.APIRouterV21()

        work_dir = Path(target_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        impl_path = Path(
            work_dir, "openapi_specs", "compute", f"v{self.api_version}.yaml"
        )
        impl_path.parent.mkdir(parents=True, exist_ok=True)

        openapi_spec = self.load_openapi(impl_path)
        if not openapi_spec:
            openapi_spec = SpecSchema(
                info=dict(
                    title="OpenStack Compute API",
                    description=LiteralScalarString(
                        "Compute API provided by Nova service"
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
            if route.routepath.startswith("/{project"):
                continue
            self._process_route(route, openapi_spec, ver_prefix="/v2.1")

        self._sanitize_param_ver_info(openapi_spec, self.min_api_version)

        if args.api_ref_src:
            merge_api_ref_doc(
                openapi_spec,
                args.api_ref_src,
                allow_strip_version=False,
                doc_url_prefix="/v2.1",
            )

        self.dump_openapi(openapi_spec, impl_path, args.validate)

        lnk = Path(impl_path.parent, "v2.yaml")
        lnk.unlink(missing_ok=True)
        lnk.symlink_to(impl_path.name)

        return impl_path

    def generate(self, target_dir, args):
        proc = Process(target=self._generate, args=[target_dir, args])
        proc.start()
        proc.join()
        if proc.exitcode != 0:
            raise RuntimeError("Error generating Compute OpenAPI schema")

    def _get_param_ref(
        self,
        openapi_spec,
        ref_name: str,
        param_name: str,
        param_location: str,
        path: str | None = None,
        **param_attrs,
    ):
        if ref_name == "os_instance_usage_audit_log_id":
            openapi_spec.components.parameters[ref_name] = ParameterSchema(
                location="path",
                name="id",
                type_schema=TypeSchema(type="string", format="date-time"),
                description="Filters the response by the date and time before which to list usage audits.",
                required=True,
            )
            ref = f"#/components/parameters/{ref_name}"
        else:
            ref = super()._get_param_ref(
                openapi_spec,
                ref_name,
                param_name=param_name,
                param_location=param_location,
                path=path,
                **param_attrs,
            )

        return ref

    def _get_schema_ref(
        self,
        openapi_spec,
        name,
        description=None,
        schema_def=None,
        action_name=None,
    ):
        from nova.api.openstack.compute.schemas import flavor_manage

        schema = None
        mime_type: str = "application/json"
        # NOTE(gtema): This must go away once scemas are merged directly to
        # Nova
        # /servers
        if name == "ServersCreateResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVER_CREATED_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"

        elif name == "ServersListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVER_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ServersDetailResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVER_LIST_DETAIL_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in ["ServerShowResponse", "ServerUpdateResponse"]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVER_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /servers/{id}/action
        elif name in [
            "ServersActionRevertresizeResponse",
            "ServersActionRebootResponse",
            "ServersActionResizeResponse",
            "ServersActionRebuildResponse",
            "ServersActionOs-StartResponse",
            "ServersActionOs-StopResponse",
            "ServersActionTrigger_Crash_DumpResponse",
            "ServersActionInjectnetworkinfoResponse",
            "ServersActionOs-ResetstateResponse",
            "ServersActionChangepasswordResponse",
            "ServersActionRestoreResponse",
            "ServersActionForcedeleteResponse",
            "ServersActionLockResponse",
            "ServersActionUnlockResponse",
            "ServersActionMigrateResponse",
            "ServersActionOs-MigrateliveResponse",
            "ServersActionPauseResponse",
            "ServersActionUnpauseResponse",
            "ServersActionUnrescueResponse",
            "ServersActionAddsecuritygroupResponse",
            "ServersActionRemovesecuritygroupResponse",
            "ServersActionShelveResponse",
            "ServersActionShelveoffloadResponse",
            "ServersActionUnshelveResponse",
            "ServersActionSuspendResponse",
            "ServersActionResumeResponse",
            "ServersActionResetnetworkResponse",
            "ServersActionAddfloatingipResponse",
            "ServersActionRemovefloatingipResponse",
            "ServersActionAddfixedipResponse",
            "ServersActionRemovefixedipResponse",
        ]:
            return (None, None)
        elif name in [
            "ServersActionCreateimageResponse",
            "ServersActionCreatebackupResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **nova_schemas.SERVER_ACTION_CREATE_IMAGE_RESPONSE_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "ServersActionEvacuateResponse",
            "ServersActionRescueResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**nova_schemas.SERVER_ACTION_NEW_ADMINPASS_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ServersActionOs-GetconsoleoutputResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **nova_schemas.SERVER_ACTION_GET_CONSOLE_OUTPUT_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "ServersActionOs-GetvncconsoleResponse",
            "ServersActionOs-GetspiceconsoleResponse",
            "ServersActionOs-GetrdpconsoleResponse",
            "ServersActionOs-GetserialconsoleResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**nova_schemas.SERVER_ACTION_REMOTE_CONSOLE_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        # /server/id/diagnostics
        elif name == "ServersDiagnosticsListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVER_DIAGNOSTICS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /server/id/ips
        elif name == "ServersIpsListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**nova_schemas.SERVER_ADDRESSES_CONTAINER_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ServersIpShowResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    maxProperties=1, **nova_schemas.SERVER_ADDRESSES_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        # /servers/id/metadata
        elif name in [
            "ServersMetadataListResponse",
            "ServersMetadataCreateResponse",
            "ServersMetadataUpdate_AllResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVER_METADATA_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in ["ServersMetadataShowResponse", "ServersMetadataUpdate"]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVER_METADATA_ITEM_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /server/id/os-instance-actions
        elif name == "ServersOs_Instance_ActionsListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**nova_schemas.SERVER_INSTANCE_ACTION_LIST_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ServersOs_Instance_ActionShowResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **nova_schemas.SERVER_INSTANCE_ACTION_CONTAINER_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        # /server/id/os-interface-attachment
        elif name == "ServersOs_InterfaceListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**nova_schemas.INTERFACE_ATTACHMENT_LIST_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "ServersOs_InterfaceCreateResponse",
            "ServersOs_InterfaceShowResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(
                    **nova_schemas.INTERFACE_ATTACHMENT_CONTAINER_SCHEMA
                ),
            )
            ref = f"#/components/schemas/{name}"
        # /server/id/os-server-password
        elif name == "ServersOs_Server_PasswordListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVER_PASSWORD_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /server/id/os-volume_attachments
        elif name == "ServersOs_Volume_AttachmentsListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.VOLUME_ATTACHMENT_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "ServersOs_Volume_AttachmentsCreateResponse",
            "ServersOs_Volume_AttachmentShowResponse",
            "ServersOs_Volume_AttachmentUpdateResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**nova_schemas.VOLUME_ATTACHMENT_CONTAINER_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"

        # /flavors/...
        elif name == "FlavorsListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.FLAVORS_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "FlavorsDetailResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.FLAVORS_LIST_DETAIL_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "FlavorsCreateResponse",
            "FlavorShowResponse",
            "FlavorUpdateResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.FLAVOR_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "FlavorUpdateRequest":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**flavor_manage.update_v2_55)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "FlavorsOs_Flavor_AccessListResponse",
            "FlavorsActionAddtenantaccessResponse",
            "FlavorsActionRemovetenantaccessResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.FLAVOR_ACCESSES_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "FlavorsOs_Extra_SpecsListResponse",
            "FlavorsOs_Extra_SpecsCreateResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.FLAVOR_EXTRA_SPECS_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "FlavorsOs_Extra_SpecShowResponse",
            "FlavorsOs_Extra_SpecUpdateResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.FLAVOR_EXTRA_SPEC_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /limits
        elif name == "LimitsListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.LIMITS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /os-aggregates
        elif name == "Os_AggregatesListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.AGGREGATE_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "Os_AggregatesCreateResponse",
            "Os_AggregateShowResponse",
            "Os_AggregateUpdateResponse",
            "Os_AggregatesActionAdd_HostResponse",
            "Os_AggregatesActionRemove_HostResponse",
            "Os_AggregatesActionSet_MetadataResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.AGGREGATE_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "Os_AggregatesImagesResponse":
            return (None, None)
        # /os-assisted-volume-snapshots
        elif name == "Os_Assisted_Volume_SnapshotsCreateResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.VOLUME_SNAPSHOT_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /os-assisted-volume-snapshots
        elif name == "Os_Assisted_Volume_SnapshotsCreateResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.VOLUME_SNAPSHOT_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /os-availability-zone
        elif name == "Os_Availability_ZoneListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.AZ_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "Os_Availability_ZoneDetailResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.AZ_LIST_DETAIL_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /os-console-auth-tokens/{id}
        elif name == "Os_Console_Auth_TokenShowResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.CONSOLE_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /servers/{id}/remote-console
        elif name == "ServersRemote_ConsolesCreateResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.REMOTE_CONSOLE_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /os-hypervisors
        elif name == "Os_HypervisorsListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.HYPERVISOR_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "Os_HypervisorsDetailResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.HYPERVISOR_LIST_DETAIL_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "Os_HypervisorShowResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.HYPERVISOR_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /os-instance_usage_audit_log
        elif name in [
            "Os_Instance_Usage_Audit_LogListResponse",
            "Os_Instance_Usage_Audit_LogShowResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.INSTANCE_USAGE_AUDIT_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /os-keypairs
        elif name == "Os_KeypairsListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.KEYPAIR_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "Os_KeypairShowResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.KEYPAIR_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "Os_KeypairsCreateResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.KEYPAIR_CREATED_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /os-migrations
        elif name == "Os_MigrationsListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.MIGRATION_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /servers/{server_id}/migrations
        elif name == "ServersMigrationsActionForce_CompleteResponse":
            return (None, None)
        elif name == "ServersMigrationsListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVER_MIGRATION_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ServersMigrationShowResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**nova_schemas.SERVER_MIGRATION_CONTAINER_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        # /os-quota
        elif name in [
            "Os_Quota_SetShowResponse",
            "Os_Quota_SetUpdateResponse",
            "Os_Quota_SetsDefaultsResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.QUOTA_SET_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "Os_Quota_SetsDetailResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**nova_schemas.QUOTA_SET_DETAIL_CONTAINER_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "Os_Quota_Class_SetShowResponse",
            "Os_Quota_Class_SetUpdate",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**nova_schemas.QUOTA_CLASS_SET_CONTAINER_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        # /os-external-events
        elif name == "Os_Server_External_EventsCreateResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.EXTERNAL_EVENTS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /os-server-groups
        elif name == "Os_Server_GroupsListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVER_GROUP_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "Os_Server_GroupsCreateResponse",
            "Os_Server_GroupShowResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVER_GROUP_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /os-services
        elif name == "Os_ServicesListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVICE_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "Os_ServiceUpdateResponse",
            "Os_Server_GroupShowResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVICE_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        # /os-simple-tenant-usage
        elif name in [
            "Os_Simple_Tenant_UsageListResponse",
            "Os_Simple_Tenant_UsageShowResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.TENANT_USAGE_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"

        # Server Topology
        elif name == "ServersTopologyListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVER_TOPOLOGY_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ServersOs_Security_GroupsListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name,
                TypeSchema(**nova_schemas.SERVER_SECURITY_GROUPS_LIST_SCHEMA),
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "ServersTagsListResponse",
            "ServersTagsUpdate_All",
            "ServersTagsUpdate_AllResponse",
        ]:
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.SERVER_TAGS_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"

        # Compute extensions
        elif name == "ExtensionsListResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.EXTENSION_LIST_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name == "ExtensionShowResponse":
            schema = openapi_spec.components.schemas.setdefault(
                name, TypeSchema(**nova_schemas.EXTENSION_CONTAINER_SCHEMA)
            )
            ref = f"#/components/schemas/{name}"
        elif name in [
            "ServersTagGetResponse",
            "ServersTagUpdateRequest",
            "ServersTagUpdateResponse",
        ]:
            # Operations without body
            return (None, None)
        else:
            (ref, mime_type) = super()._get_schema_ref(
                openapi_spec, name, description, action_name=action_name
            )
        if action_name and schema:
            if not schema.openstack:
                schema.openstack = {}
            schema.openstack.setdefault("action-name", action_name)

        if schema:
            print(schema.model_dump())
        return (ref, mime_type)

    def _post_process_operation_hook(
        self, openapi_spec, operation_spec, path: str | None = None
    ):
        """Hook to allow service specific generator to modify details"""
        if operation_spec.operationId == "servers/id/action:post":
            # Sereral server actions may return Location header
            operation_spec.responses.setdefault(
                "202", {"description": "Accepted"}
            )
            headers_202 = operation_spec.responses["202"].setdefault(
                "headers", {}
            )
            headers_202.setdefault(
                "Location",
                HeaderSchema(
                    description='The image location URL of the image or backup created, HTTP header "Location: <image location URL>" will be returned. May be returned only in response of `createBackup` and `createImage` actions.',
                    schema=TypeSchema(type="string"),
                    openstack={"max-ver": "2.44"},
                ),
            )
        super()._post_process_operation_hook(openapi_spec, operation_spec)
