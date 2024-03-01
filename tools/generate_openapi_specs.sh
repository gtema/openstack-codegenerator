#!/usr/bin/bash -e

API_REF_BUILD_ROOT=~/workspace/opendev/openstack
openstack-codegenerator --work-dir wrk --target openapi-spec --service-type compute --api-ref-src ${API_REF_BUILD_ROOT}/nova/api-ref/build/html/index.html
openstack-codegenerator --work-dir wrk --target openapi-spec --service-type network --api-ref-src ${API_REF_BUILD_ROOT}/neutron-lib/api-ref/build/html/v2/index.html
openstack-codegenerator --work-dir wrk --target openapi-spec --service-type volume --api-ref-src ${API_REF_BUILD_ROOT}/cinder/api-ref/build/html/v3/index.html
openstack-codegenerator --work-dir wrk --target openapi-spec --service-type image --api-ref-src ${API_REF_BUILD_ROOT}/glance/api-ref/build/html/v2/index.html
sed -i "s|\[API versions call\](../versions/index.html#versions-call)|API versions call|g" wrk/openapi_specs/image/v2.yaml
openstack-codegenerator --work-dir wrk --target openapi-spec --service-type identity --api-ref-src ${API_REF_BUILD_ROOT}/keystone/api-ref/build/html/v3/index.html
openstack-codegenerator --work-dir wrk --target openapi-spec --service-type load-balancing --api-ref-src ${API_REF_BUILD_ROOT}/octavia/api-ref/build/html/v2/index.html
openstack-codegenerator --work-dir wrk --target openapi-spec --service-type placement --api-ref-src ${API_REF_BUILD_ROOT}/placement/api-ref/build/html/index.html
sed -i "s/(?expanded=delete-resource-provider-inventories-detail#delete-resource-provider-inventories)//" wrk/openapi_specs/placement/v1.yaml
