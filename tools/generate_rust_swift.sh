#!/usr/bin/bash -e
#
DATA=(
# Object Store
# sdk
# account
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id account.get --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name account"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id account.head --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name account"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id account.post --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name account"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id account.delete --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name account"
# container
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id container.get --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name container"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id container.head --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name container"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id container.put --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name container"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id container.post --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name container"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id container.delete --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name container"
# object
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id object.head --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name object"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id object.get --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name object"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id object.put --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name object"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id object.post --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name object"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id object.delete --target rust-sdk --service-type object-store --api-version v1 --alternative-target-name object"

# cli
# account
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id account.head --target rust-cli --service-type object-store --api-version v1 --alternative-target-name account"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id account.post --target rust-cli --service-type object-store --api-version v1 --command-type set --alternative-target-name account"

# container
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id account.get --target rust-cli --service-type object-store --api-version v1 --alternative-target-name container --sdk-mod-path account::get --command-type list"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id container.head --target rust-cli --service-type object-store --api-version v1 --alternative-target-name container --command-type show"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id container.post --target rust-cli --service-type object-store --api-version v1 --alternative-target-name container --command-type set"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id container.put --target rust-cli --service-type object-store --api-version v1 --alternative-target-name container --command-type create"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id container.delete --target rust-cli --service-type object-store --api-version v1 --alternative-target-name container --command-type delete"

#object
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id container.get --target rust-cli --service-type object-store --api-version v1 --alternative-target-name object --sdk-mod-path container::get --command-type list"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id object.put --target rust-cli --service-type object-store --api-version v1 --alternative-target-name object --command-type upload"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id object.get --target rust-cli --service-type object-store --api-version v1 --alternative-target-name object --command-type download"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id object.head --target rust-cli --service-type object-store --api-version v1 --alternative-target-name object --command-type show"
"--openapi-yaml-spec openapi_specs/object-store/swift.spec.yaml --openapi-operation-id object.delete --target rust-cli --service-type object-store --api-version v1 --alternative-target-name object --command-type delete"
)

for item in "${DATA[@]}"; do
  python codegenerator/cli.py $item --work-dir wrk
done;

