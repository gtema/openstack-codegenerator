#!/usr/bin/bash -e

WRK_DIR=wrk
METADATA=metadata
DST=~/workspace/github/gtema/openstack
NET_RESOURCES=(
  "availability_zone"
  "extension"
  "floatingip"
  "network"
  "port"
  "router"
  "subnet"
)

openstack-codegenerator --work-dir ${WRK_DIR} --target rust-sdk --metadata ${METADATA}/network_metadata.yaml --service network
openstack-codegenerator --work-dir ${WRK_DIR} --target rust-cli --metadata ${METADATA}/network_metadata.yaml --service network


for resource in "${NET_RESOURCES[@]}"; do
#  openstack-codegenerator --work-dir ${WRK_DIR} --target rust-sdk --metadata ${METADATA}/network_metadata.yaml --service network # --resource ${resource}
#  openstack-codegenerator --work-dir ${WRK_DIR} --target rust-cli --metadata ${METADATA}/network_metadata.yaml --service network # --resource ${resource}

  cp -av "${WRK_DIR}/rust/openstack_sdk/src/api/network/v2/${resource}" ${DST}/openstack_sdk/src/api/network/v2
  cp -av "${WRK_DIR}/rust/openstack_sdk/src/api/network/v2/${resource}.rs" ${DST}/openstack_sdk/src/api/network/v2
  cp -av "${WRK_DIR}/rust/openstack_cli/src/network/v2/${resource}" ${DST}/openstack_cli/src/network/v2
done;
