#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

import argparse
import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
import re
import sys

from openstack import resource
from sphinx import pycode
import yaml

from codegenerator.ansible import AnsibleGenerator
from codegenerator import common
from codegenerator.jsonschema import JsonSchemaGenerator
from codegenerator.metadata import MetadataGenerator
from codegenerator.openapi_spec import OpenApiSchemaGenerator
from codegenerator.osc import OSCGenerator
from codegenerator.rust_cli import RustCliGenerator
from codegenerator.rust_sdk import RustSdkGenerator
from codegenerator.types import Metadata


class ResourceProcessor:
    def __init__(self, mod_name, class_name):
        self.mod_name = mod_name
        self.class_name = class_name
        self.class_plural_name = (
            class_name + "s" if class_name[:-1] != "y" else "ies"
        )

        spec = importlib.util.find_spec(self.mod_name)
        if not spec:
            raise RuntimeError("Module %s not found" % self.mod_name)
        self.module = importlib.util.module_from_spec(spec)
        if not self.module:
            raise RuntimeError("Error loading module %s" % self.mod_name)
        sys.modules[self.mod_name] = self.module
        if not spec.loader:
            raise RuntimeError("No module loader available")
        spec.loader.exec_module(self.module)
        self.resource_class = getattr(self.module, self.class_name)

        # Get resource proxy
        srv_ver_mod, _, _ = self.mod_name.rpartition(".")
        proxy_mod_name = srv_ver_mod + "._proxy"
        proxy_spec = importlib.util.find_spec(proxy_mod_name)
        if not proxy_spec:
            raise RuntimeError("Module %s not found" % proxy_mod_name)
        self.proxy_mod = importlib.util.module_from_spec(proxy_spec)
        if not self.proxy_mod:
            raise RuntimeError("Error loading module %s" % proxy_mod_name)
        sys.modules[proxy_mod_name] = self.proxy_mod
        if not proxy_spec.loader:
            raise RuntimeError("No module loader available")
        proxy_spec.loader.exec_module(self.proxy_mod)
        self.proxy_obj = getattr(self.proxy_mod, "Proxy")
        self.srv_ver_mod = srv_ver_mod

        self.service_name = self.mod_name.split(".")[1]
        self.fqcn = f"{self.mod_name}.{self.class_name}"

        # Find the resource registry name
        for k, v in self.proxy_obj._resource_registry.items():
            if (
                hasattr(v, "__module__")
                and v.__module__ == self.mod_name
                and v.__name__ == self.class_name
            ):
                self.registry_name = f"{self.service_name}.{k}"

        self.attrs = dict()
        self.process()

    def process(self):
        attr_docs = self.get_attr_docs()
        for k, v in self.body_attrs():
            doc = attr_docs.get(k)
            if doc:
                doc = re.sub("\\*Type: .*\\*", "", doc)
                doc = doc.rstrip()
            if not doc and k == "name":
                doc = "Name"
            elif not doc and k == "tags":
                doc = f"{self.class_name} Tags."
            self.attrs[k] = dict(attr=v, docs=doc)

    def get_attr_docs(self):
        mod = pycode.ModuleAnalyzer.for_module(self.mod_name)
        mod.analyze()
        result = {}
        for k, v in mod.attr_docs.items():
            if k[0] == self.class_name:
                result[k[1]] = " ".join(v)
        if "id" not in result:
            result["id"] = "Id of the resource"
        return result

    def body_attrs(self):
        for attr in inspect.getmembers(self.resource_class):
            if isinstance(attr[1], resource.Body):
                yield attr


class Generator:
    schemas: dict = {}
    metadata: Metadata

    def get_openapi_spec(self, path: Path):
        logging.debug("Fetch %s", path)
        if path.as_posix() not in self.schemas:
            self.schemas[path.as_posix()] = common.get_openapi_spec(
                path.as_posix()
            )
        return self.schemas[path.as_posix()]

    def load_metadata(self, path: Path):
        with open(path, "r") as fp:
            data = yaml.safe_load(fp)
        self.metadata = Metadata(**data)


def main():
    parser = argparse.ArgumentParser(
        description="Generate code from OpenStackSDK resource definitions"
    )
    parser.add_argument(
        "--module",
        #        required=True,
        help="OpenStackSDK Module name (i.e. openstack.identity.v3.project)",
    )
    parser.add_argument(
        "--class-name",
        # required=True,
        help="OpenStackSDK Class name (under the specified module)",
    )
    parser.add_argument(
        "--target",
        required=True,
        choices=[
            "osc",
            "ansible",
            "rust-sdk",
            "rust-cli",
            "openapi-spec",
            "jsonschema",
            "metadata",
        ],
        help="Target for which to generate code",
    )
    parser.add_argument(
        "--work-dir", help="Working directory for the generated code"
    )
    parser.add_argument(
        "--alternative-module-path",
        help=("Optional new module path"),
    )
    parser.add_argument(
        "--alternative-module-name",
        help=("Optional new module name " "(rename get into list)"),
    )
    parser.add_argument(
        "--openapi-yaml-spec",
        help=("Path to the OpenAPI spec file (yaml)"),
    )
    parser.add_argument(
        "--openapi-operation-id",
        help=("OpenAPI operationID"),
    )
    parser.add_argument(
        "--service-type",
        help=("Catalog service type"),
    )

    parser.add_argument(
        "--api-version",
        help=("Api version (used in path for resulting code, i.e. v1)"),
    )

    parser.add_argument(
        "--metadata",
        help=("Metadata file to load"),
    )
    parser.add_argument(
        "--service",
        help=("Metadata service name filter"),
    )
    parser.add_argument(
        "--resource",
        help=("Metadata resource name filter"),
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help=("Metadata resource name filter"),
    )

    generators = {
        "osc": OSCGenerator(),
        "ansible": AnsibleGenerator(),
        "rust-sdk": RustSdkGenerator(),
        "rust-cli": RustCliGenerator(),
        "openapi-spec": OpenApiSchemaGenerator(),
        "jsonschema": JsonSchemaGenerator(),
        "metadata": MetadataGenerator(),
    }

    for g, v in generators.items():
        v.get_parser(parser)

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    generator = Generator()

    if args.metadata:
        metadata_path = Path(args.metadata)
        generator.load_metadata(metadata_path)
        # Resulting mod_paths
        res_mods = []

        for res, res_data in generator.metadata.resources.items():
            if args.service and not res.startswith(args.service):
                continue
            if args.resource and res != f"{args.service}.{args.resource}":
                continue
            for op, op_data in res_data.operations.items():
                logging.debug(f"Processing operation {op_data.operation_id}")
                if args.target in op_data.targets:
                    op_args = op_data.targets[args.target]
                    if not op_args.service_type:
                        op_args.service_type = res.split(".")[0]
                    if not op_args.api_version:
                        op_args.api_version = res_data.api_version
                    if not op_args.operation_type and op_data.operation_type:
                        op_args.operation_type = op_data.operation_type
                    # if not op_data.alternative_module_name and args.target == "rust-sdk":

                    openapi_spec = generator.get_openapi_spec(
                        Path(
                            # metadata_path.parent,
                            op_data.spec_file
                            or res_data.spec_file,
                        ).resolve()
                    )

                    for mod_path, mod_name, path in generators[
                        args.target
                    ].generate(
                        res,
                        args.work_dir,
                        openapi_spec=openapi_spec,
                        operation_id=op_data.operation_id,
                        args=op_args,
                    ):
                        res_mods.append((mod_path, mod_name, path))
            rust_sdk_extensions = res_data.extensions.get("rust-sdk")
            if rust_sdk_extensions:
                additional_modules = rust_sdk_extensions.setdefault(
                    "additional_modules", []
                )
                res_x = res.split(".")
                for mod in additional_modules:
                    res_mods.append(
                        (
                            [
                                res_x[0].replace("-", "_"),
                                res_data.api_version,
                                res_x[1],
                            ],
                            mod,
                            "",
                        )
                    )

        if args.target == "rust-sdk" and not args.resource:
            resource_results: dict[str, dict] = dict()
            for mod_path, mod_name, path in res_mods:
                mn = "/".join(mod_path)
                x = resource_results.setdefault(
                    mn, {"path": path, "mods": set()}
                )
                x["mods"].add(mod_name)
            changed = True
            while changed:
                changed = False
                for mod_path in [
                    mod_path_str.split("/")
                    for mod_path_str in resource_results.keys()
                ]:
                    if len(mod_path) < 3:
                        continue
                    mn = "/".join(mod_path[0:-1])
                    mod_name = mod_path[-1]
                    if mn in resource_results:
                        if mod_name not in resource_results[mn]["mods"]:
                            resource_results[mn]["mods"].add(mod_name)
                            changed = True
                    else:
                        changed = True
                        x = resource_results.setdefault(
                            mn, {"path": path, "mods": set()}
                        )
                        x["mods"].add(mod_name)

                for path, gen_data in resource_results.items():
                    generators["rust-sdk"].generate_mod(
                        args.work_dir,
                        path.split("/"),
                        gen_data["mods"],
                        gen_data["path"],
                        res.split(".")[-1].capitalize(),
                        service_name=path.split("/")[0],
                    )
        exit(0)

    rp = None
    if args.module and args.class_name:
        rp = ResourceProcessor(args.module, args.class_name)

    generators[args.target].generate(
        rp,
        args.work_dir,
        openapi_spec=None,
        operation_id=args.openapi_operation_id,
        args=args,
    )


if __name__ == "__main__":
    main()
