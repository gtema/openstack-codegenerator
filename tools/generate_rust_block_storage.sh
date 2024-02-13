#!/usr/bin/bash -e
#

WRK_DIR=wrk
METADATA=metadata
DST=~/workspace/github/gtema/openstack
NET_RESOURCES=(
  "volume"
  "type"
)

openstack-codegenerator --work-dir ${WRK_DIR} --target rust-sdk --metadata ${METADATA}/block-storage_metadata.yaml --service block-storage
openstack-codegenerator --work-dir ${WRK_DIR} --target rust-cli --metadata ${METADATA}/block-storage_metadata.yaml --service block-storage


for resource in "${NET_RESOURCES[@]}"; do
  cp -av "${WRK_DIR}/rust/openstack_sdk/src/api/block_storage/v3/${resource}" ${DST}/openstack_sdk/src/api/block_storage/v3
  cp -av "${WRK_DIR}/rust/openstack_sdk/src/api/block_storage/v3/${resource}.rs" ${DST}/openstack_sdk/src/api/block_storage/v3
  cp -av "${WRK_DIR}/rust/openstack_cli/src/block_storage/v3/${resource}" ${DST}/openstack_cli/src/block_storage/v3
done;
