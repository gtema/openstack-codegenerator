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

import logging

from codegenerator.base import BaseGenerator


class OpenApiSchemaGenerator(BaseGenerator):
    def __init__(self):
        super().__init__()

    def get_parser(self, parser):
        parser.add_argument(
            "--api-ref-src",
            help="Path to the rendered api-ref html to extract descriptions",
        )
        return parser

    def generate_nova(self, target_dir, args):
        from codegenerator.openapi.nova import NovaGenerator

        NovaGenerator().generate(target_dir, args)

    def generate_cinder(self, target_dir, args):
        from codegenerator.openapi.cinder import CinderV3Generator

        CinderV3Generator().generate(target_dir, args)

    def generate_glance(self, target_dir, args):
        from codegenerator.openapi.glance import GlanceGenerator

        GlanceGenerator().generate(target_dir, args)

    def generate_keystone(self, target_dir, args):
        from codegenerator.openapi.keystone import KeystoneGenerator

        KeystoneGenerator().generate(target_dir, args)

    def generate_octavia(self, target_dir, args):
        from codegenerator.openapi.octavia import OctaviaGenerator

        OctaviaGenerator().generate(target_dir, args)

    def generate_neutron(self, target_dir, args):
        from codegenerator.openapi.neutron import NeutronGenerator

        NeutronGenerator().generate(target_dir, args)

    def generate_placement(self, target_dir, args):
        from codegenerator.openapi.placement import PlacementGenerator

        PlacementGenerator().generate(target_dir, args)

    def generate(
        self, res, target_dir, openapi_spec=None, operation_id=None, args=None
    ):
        """Generate Schema definition file for Resource"""
        logging.debug("Generating OpenAPI schema data in %s" % target_dir)
        # We do not import generators since due to the use of Singletons in the
        # code importing glance, nova, cinder at the same time crashes
        # dramatically
        if args.service_type == "compute":
            self.generate_nova(target_dir, args)
        elif args.service_type in ["block-storage", "volume"]:
            self.generate_cinder(target_dir, args)
        elif args.service_type == "image":
            self.generate_glance(target_dir, args)
        elif args.service_type == "identity":
            self.generate_keystone(target_dir, args)
        elif args.service_type == "load-balancing":
            self.generate_octavia(target_dir, args)
        elif args.service_type == "network":
            self.generate_neutron(target_dir, args)
        elif args.service_type == "placement":
            self.generate_placement(target_dir, args)
        else:
            raise RuntimeError(
                "Service type %s is not supported", args.service_type
            )
