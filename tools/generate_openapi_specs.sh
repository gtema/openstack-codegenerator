#!/usr/bin/bash -e

API_REF_BUILD_ROOT=~/workspace/opendev/openstack
#openstack-codegenerator --work-dir wrk --target openapi-spec --service-type compute --api-ref-src ${API_REF_BUILD_ROOT}/nova/api-ref/build/html/index.html
#openstack-codegenerator --work-dir wrk --target openapi-spec --service-type network --api-ref-src ${API_REF_BUILD_ROOT}/neutron-lib/api-ref/build/html/v2/index.html
openstack-codegenerator --work-dir wrk --target openapi-spec --service-type volume --api-ref-src ${API_REF_BUILD_ROOT}/cinder/api-ref/build/html/v3/index.html
openstack-codegenerator --work-dir wrk --target openapi-spec --service-type image --api-ref-src ${API_REF_BUILD_ROOT}/glance/api-ref/build/html/v2/index.html
#openstack-codegenerator --work-dir wrk --target openapi-spec --service-type identity --api-ref-src ${API_REF_BUILD_ROOT}/keystone/api-ref/build/html/v3/index.html
#openstack-codegenerator --work-dir wrk --target openapi-spec --service-type load-balancing --api-ref-src ${API_REF_BUILD_ROOT}/octavia/api-ref/build/html/v2/index.html
