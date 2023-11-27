#!/usr/bin/env bash
#
DATA=(
# Compute
#
# sdk
# server
"--openapi-yaml-spec openapi_specs/compute/server.spec.yaml --openapi-operation-id server.get --target rust-sdk --service-type compute --api-version v2"
"--openapi-yaml-spec openapi_specs/compute/server.spec.yaml --openapi-operation-id servers.get --target rust-sdk --service-type compute --api-version v2"
"--openapi-yaml-spec openapi_specs/compute/server.spec.yaml --openapi-operation-id servers.get_detailed --target rust-sdk --service-type compute --api-version v2"
"--openapi-yaml-spec openapi_specs/compute/server_action.pause.yaml --openapi-operation-id server.action.pause --target rust-sdk --service-type compute --api-version v2 --alternative-method-name pause"
# flavor
"--openapi-yaml-spec openapi_specs/compute/flavor.spec.yaml --openapi-operation-id flavor.get --target rust-sdk --service-type compute --api-version v2"
"--openapi-yaml-spec openapi_specs/compute/flavor.spec.yaml --openapi-operation-id flavors.get --target rust-sdk --service-type compute --api-version v2"
"--openapi-yaml-spec openapi_specs/compute/flavor.spec.yaml --openapi-operation-id flavors.get_detailed --target rust-sdk --service-type compute --api-version v2"
# keypairs
"--openapi-yaml-spec openapi_specs/compute/keypair.spec.yaml --openapi-operation-id keypairs.get --target rust-sdk --service-type compute --api-version v2 --command-type list --response-key keypairs --response-list-item-key keypair"
"--openapi-yaml-spec openapi_specs/compute/keypair.spec.yaml --openapi-operation-id keypairs.post --target rust-sdk --service-type compute --api-version v2"
"--openapi-yaml-spec openapi_specs/compute/keypair.spec.yaml --openapi-operation-id keypair.get --target rust-sdk --service-type compute --api-version v2"
"--openapi-yaml-spec openapi_specs/compute/keypair.spec.yaml --openapi-operation-id keypair.delete --target rust-sdk --service-type compute --api-version v2"
# cli
# server
"--openapi-yaml-spec openapi_specs/compute/server.spec.yaml --openapi-operation-id servers.get_detailed --target rust-cli --service-type compute --api-version v2 --command-type list --alternative-target-name server --sdk-mod-path servers::detail::get"
"--openapi-yaml-spec openapi_specs/compute/server.spec.yaml --openapi-operation-id server.get --target rust-cli --service-type compute --api-version v2 --command-type show --alternative-target-name server --sdk-mod-path server::get"
# flavor
"--openapi-yaml-spec openapi_specs/compute/flavor.spec.yaml --openapi-operation-id flavors.get_detailed --target rust-cli --service-type compute --api-version v2 --command-type list --alternative-target-name flavor --sdk-mod-path flavors::detail::get"
"--openapi-yaml-spec openapi_specs/compute/flavor.spec.yaml --openapi-operation-id flavor.get --target rust-cli --service-type compute --api-version v2 --command-type show --alternative-target-name flavor --sdk-mod-path flavor::get --command-type show"
# keypair
"--openapi-yaml-spec openapi_specs/compute/keypair.spec.yaml --openapi-operation-id keypairs.get --target rust-cli --service-type compute --api-version v2 --command-type list --alternative-target-name keypair --sdk-mod-path os_keypairs::get"
"--openapi-yaml-spec openapi_specs/compute/keypair.spec.yaml --openapi-operation-id keypairs.post --target rust-cli --service-type compute --api-version v2 --command-type create --alternative-target-name keypair --sdk-mod-path os_keypairs::post"
"--openapi-yaml-spec openapi_specs/compute/keypair.spec.yaml --openapi-operation-id keypair.get --target rust-cli --service-type compute --api-version v2 --command-type show"
"--openapi-yaml-spec openapi_specs/compute/keypair.spec.yaml --openapi-operation-id keypair.delete --target rust-cli --service-type compute --api-version v2 --command-type delete"
)

for item in "${DATA[@]}"; do
  python codegenerator/cli.py $item --work-dir wrk
done;

