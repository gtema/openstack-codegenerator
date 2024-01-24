#!/usr/bin/bash -e

openstack-codegenerator --work-dir metadata --target metadata --openapi-yaml-spec wrk/openapi_specs/block-storage/v3.yaml --service-type block-storage
openstack-codegenerator --work-dir metadata --target metadata --openapi-yaml-spec wrk/openapi_specs/compute/v2.yaml --service-type compute
openstack-codegenerator --work-dir metadata --target metadata --openapi-yaml-spec wrk/openapi_specs/identity/v3.yaml --service-type identity
openstack-codegenerator --work-dir metadata --target metadata --openapi-yaml-spec wrk/openapi_specs/image/v2.yaml --service-type image
openstack-codegenerator --work-dir metadata --target metadata --openapi-yaml-spec wrk/openapi_specs/network/v2.yaml --service-type network

tools/generate_rust_block_storage.sh
tools/generate_rust_compute.sh
tools/generate_rust_identity.sh
tools/generate_rust_image.sh
tools/generate_rust_network.sh
