#!/usr/bin/bash -e

WRK_DIR=wrk
METADATA=metadata
DST=~/workspace/github/gtema/openstack
NET_RESOURCES=(
  "image"
  "schema"
  "metadef"
)

openstack-codegenerator --work-dir ${WRK_DIR} --target rust-sdk --metadata ${METADATA}/image_metadata.yaml --service image
openstack-codegenerator --work-dir ${WRK_DIR} --target rust-cli --metadata ${METADATA}/image_metadata.yaml --service image


for resource in "${NET_RESOURCES[@]}"; do
  cp -av "${WRK_DIR}/rust/openstack_sdk/src/api/image/v2/${resource}" ${DST}/openstack_sdk/src/api/image/v2
  cp -av "${WRK_DIR}/rust/openstack_sdk/src/api/image/v2/${resource}.rs" ${DST}/openstack_sdk/src/api/image/v2
  cp -av "${WRK_DIR}/rust/openstack_cli/src/image/v2/${resource}" ${DST}/openstack_cli/src/image/v2
  cp -av "${WRK_DIR}/rust/openstack_cli/tests/image/v2/${resource}" ${DST}/openstack_cli/tests/image/v2
done;
