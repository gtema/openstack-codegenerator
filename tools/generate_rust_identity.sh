#!/usr/bin/bash -e

WRK_DIR=wrk
METADATA=metadata
DST=~/workspace/github/gtema/openstack
NET_RESOURCES=(
  "auth"
  "group"
  "os_federation"
  "endpoint"
  "region"
  "role_assignment"
  "role_inference"
  "role"
  "service"
  "project"
  "user"
)

openstack-codegenerator --work-dir ${WRK_DIR} --target rust-sdk --metadata ${METADATA}/identity_metadata.yaml --service identity
openstack-codegenerator --work-dir ${WRK_DIR} --target rust-cli --metadata ${METADATA}/identity_metadata.yaml --service identity


for resource in "${NET_RESOURCES[@]}"; do
  cp -av "${WRK_DIR}/rust/openstack_sdk/src/api/identity/v3/${resource}" ${DST}/openstack_sdk/src/api/identity/v3
  cp -av "${WRK_DIR}/rust/openstack_sdk/src/api/identity/v3/${resource}.rs" ${DST}/openstack_sdk/src/api/identity/v3
  cp -av "${WRK_DIR}/rust/openstack_cli/src/identity/v3/${resource}" ${DST}/openstack_cli/src/identity/v3
done;
