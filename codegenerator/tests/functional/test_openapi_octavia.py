# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
import tempfile
from pathlib import Path
from unittest import TestCase


class Args:
    def __init__(self, validate: bool = False):
        self.validate: bool = validate
        self.api_ref_src: str | None = None


class TestGenerator(TestCase):
    def test_generate(self):
        from codegenerator.openapi import octavia

        generator = octavia.OctaviaGenerator()
        work_dir = tempfile.TemporaryDirectory()

        generator.generate(work_dir.name, Args(validate=True))

        self.assertTrue(
            Path(
                work_dir.name, "openapi_specs", "load-balancing", "v2.yaml"
            ).exists()
        )