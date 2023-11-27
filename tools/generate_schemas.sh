#!/usr/bin/env bash
#

DATA=(
  "openstack.compute.v2.server Server"
  "openstack.image.v2.image Image"
)

for item in "${DATA[@]}"; do
  IFS=" " set -- $item
  mod=$1
  class=$2
  python codegenerator/cli.py --module $mod --class-name $class --target openapi-schema --work-dir wrk
done;

