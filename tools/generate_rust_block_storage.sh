#!/usr/bin/env bash
#
DATA=(
# Block Storage
#
# sdk
# image
"--openapi-yaml-spec openapi_specs/block_storage/v3/volume.spec.yaml --openapi-operation-id volumes.get --target rust-sdk --service-type block_storage --api-version v3 --command-type list"
"--openapi-yaml-spec openapi_specs/block_storage/v3/volume.spec.yaml --openapi-operation-id volumes.get_detail --target rust-sdk --service-type block_storage --api-version v3 --command-type list"
"--openapi-yaml-spec openapi_specs/block_storage/v3/volume.spec.yaml --openapi-operation-id volume.get --target rust-sdk --service-type block_storage --api-version v3 --command-type show"
# cli
# image
"--openapi-yaml-spec openapi_specs/block_storage/v3/volume.spec.yaml --openapi-operation-id volumes.get_detail --target rust-cli --service-type block_storage --api-version v3 --command-type list --alternative-target-name volume --sdk-mod-path volumes::detail::get"
"--openapi-yaml-spec openapi_specs/block_storage/v3/volume.spec.yaml --openapi-operation-id volume.get --target rust-cli --service-type block_storage --api-version v3 --command-type show"
)

for item in "${DATA[@]}"; do
  python codegenerator/cli.py $item --work-dir wrk
done;

