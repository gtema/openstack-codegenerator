#!/usr/bin/bash -e

WRK_DIR=wrk
METADATA=metadata
DST=~/workspace/github/gtema/openstack
NET_RESOURCES=(
  "extension"
  "flavor"
  "aggregate"
  "availability_zone"
  "hypervisor"
  "keypair"
  "server"
)

openstack-codegenerator --work-dir ${WRK_DIR} --target rust-sdk --metadata ${METADATA}/compute_metadata.yaml --service compute
openstack-codegenerator --work-dir ${WRK_DIR} --target rust-cli --metadata ${METADATA}/compute_metadata.yaml --service compute

for resource in "${NET_RESOURCES[@]}"; do
  cp -av "${WRK_DIR}/rust/openstack_sdk/src/api/compute/v2/${resource}" ${DST}/openstack_sdk/src/api/compute/v2
  cp -av "${WRK_DIR}/rust/openstack_sdk/src/api/compute/v2/${resource}.rs" ${DST}/openstack_sdk/src/api/compute/v2
  cp -av "${WRK_DIR}/rust/openstack_cli/src/compute/v2/${resource}" ${DST}/openstack_cli/src/compute/v2
done;
