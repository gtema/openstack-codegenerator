#!/usr/bin/bash -e

SERVICE=$1

API_REF_BUILD_ROOT=~/workspace/opendev/openstack

if [ -z "$1" -o "$1" = "compute" ]; then
  openstack-codegenerator --work-dir wrk --target openapi-spec --service-type compute --api-ref-src ${API_REF_BUILD_ROOT}/nova/api-ref/build/html/index.html
fi
if [ -z "$1" -o "$1" = "network" ]; then
  openstack-codegenerator --work-dir wrk --target openapi-spec --service-type network --api-ref-src ${API_REF_BUILD_ROOT}/neutron-lib/api-ref/build/html/v2/index.html
fi
if [ -z "$1" -o "$1" = "block-storage" ]; then
  openstack-codegenerator --work-dir wrk --target openapi-spec --service-type volume --api-ref-src ${API_REF_BUILD_ROOT}/cinder/api-ref/build/html/v3/index.html
fi
if [ -z "$1" -o "$1" = "image" ]; then
  openstack-codegenerator --work-dir wrk --target openapi-spec --service-type image --api-ref-src ${API_REF_BUILD_ROOT}/glance/api-ref/build/html/v2/index.html --api-ref-src ${API_REF_BUILD_ROOT}/glance/api-ref/build/html/v2/metadefs-index.html

  sed -i "s|\[API versions call\](../versions/index.html#versions-call)|API versions call|g" wrk/openapi_specs/image/v2.yaml
fi
if [ -z "$1" -o "$1" = "identity" ]; then
 openstack-codegenerator --work-dir wrk --target openapi-spec --service-type identity --api-ref-src ${API_REF_BUILD_ROOT}/keystone/api-ref/build/html/v3/index.html --api-ref-src ${API_REF_BUILD_ROOT}/keystone/api-ref/build/html/v3-ext/index.html
fi
if [ -z "$1" -o "$1" = "load-balancing" ]; then
  openstack-codegenerator --work-dir wrk --target openapi-spec --service-type load-balancing --api-ref-src ${API_REF_BUILD_ROOT}/octavia/api-ref/build/html/v2/index.html
fi
if [ -z "$1" -o "$1" = "placement" ]; then
  openstack-codegenerator --work-dir wrk --target openapi-spec --service-type placement --api-ref-src ${API_REF_BUILD_ROOT}/placement/api-ref/build/html/index.html
  sed -i "s/(?expanded=delete-resource-provider-inventories-detail#delete-resource-provider-inventories)//" wrk/openapi_specs/placement/v1.yaml
fi
