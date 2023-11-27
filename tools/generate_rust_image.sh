#!/usr/bin/env bash
#
DATA=(
# Image
#
# sdk
# image
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.get --target rust-sdk --service-type image --api-version v2"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.post --target rust-sdk --service-type image --api-version v2"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.patch --target rust-sdk --service-type image --api-version v2"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.delete --target rust-sdk --service-type image --api-version v2"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.download --target rust-sdk --service-type image --api-version v2"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.upload --target rust-sdk --service-type image --api-version v2"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.deactivate --target rust-sdk --service-type image --api-version v2"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.reactivate --target rust-sdk --service-type image --api-version v2"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id images.get --target rust-sdk --service-type image --api-version v2 --command-type list"
# # schemas
"--openapi-yaml-spec openapi_specs/image/schemas.yaml --openapi-operation-id schema.image.get --target rust-sdk --service-type image --api-version v2"
"--openapi-yaml-spec openapi_specs/image/schemas.yaml --openapi-operation-id schema.images.get --target rust-sdk --service-type image --api-version v2"
"--openapi-yaml-spec openapi_specs/image/schemas.yaml --openapi-operation-id schema.member.get --target rust-sdk --service-type image --api-version v2"
"--openapi-yaml-spec openapi_specs/image/schemas.yaml --openapi-operation-id schema.members.get --target rust-sdk --service-type image --api-version v2"
# cli
# image
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id images.get --target rust-cli --service-type image --api-version v2 --command-type list --alternative-target-name image --sdk-mod-path images::get"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.get --target rust-cli --service-type image --api-version v2 --command-type show --alternative-target-name image --sdk-mod-path image::get"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.post --target rust-cli --service-type image --api-version v2 --command-type create --alternative-target-name image --sdk-mod-path images::post"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.patch --target rust-cli --service-type image --api-version v2 --command-type set --alternative-target-name image"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.delete --target rust-cli --service-type image --api-version v2 --command-type delete --alternative-target-name image"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.deactivate --target rust-cli --service-type image --api-version v2 --command-type action --command-name deactivate"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.reactivate --target rust-cli --service-type image --api-version v2 --command-type action --command-name reactivate"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.download --target rust-cli --service-type image --api-version v2 --command-type download --alternative-target-name image --sdk-mod-path image::file::get"
"--openapi-yaml-spec openapi_specs/image/image.spec.yaml --openapi-operation-id image.upload --target rust-cli --service-type image --api-version v2 --command-type upload --alternative-target-name image --sdk-mod-path image::file::put"
# Schemas
"--openapi-yaml-spec openapi_specs/image/schemas.yaml --openapi-operation-id schema.image.get --target rust-cli --service-type image --api-version v2 --alternative-target-name image --sdk-mod-path schemas::image::get --cli-mod-path schema::image::show --command-type json"
"--openapi-yaml-spec openapi_specs/image/schemas.yaml --openapi-operation-id schema.images.get --target rust-cli --service-type image --api-version v2 --alternative-target-name images --sdk-mod-path schemas::images::get --cli-mod-path schema::images::show --command-type json"
"--openapi-yaml-spec openapi_specs/image/schemas.yaml --openapi-operation-id schema.member.get --target rust-cli --service-type image --api-version v2 --alternative-target-name member --sdk-mod-path schemas::member::get --cli-mod-path schema::member::show --command-type json"
"--openapi-yaml-spec openapi_specs/image/schemas.yaml --openapi-operation-id schema.members.get --target rust-cli --service-type image --api-version v2 --alternative-target-name members --sdk-mod-path schemas::members::get --cli-mod-path schema::members::show --command-type json"
)

for item in "${DATA[@]}"; do
  python codegenerator/cli.py $item --work-dir wrk
done;

