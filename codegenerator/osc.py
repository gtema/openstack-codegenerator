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
from pathlib import Path

from codegenerator.base import BaseGenerator


class OSCGenerator(BaseGenerator):
    def __init__(self):
        super().__init__()

    def _render_command(
        self,
        context: dict,
        osc_path: list,
        impl_template: str,
        impl_dest: Path,
        test_template: str,
        test_dest: Path,
    ):
        """Render command code"""
        self._render(impl_template, context, impl_dest.parent, impl_dest.name)

        unittest_path = test_dest.parent

        unittest_path.mkdir(parents=True, exist_ok=True)
        Path(unittest_path, "__init__.py").touch()

        self._render(test_template, context, test_dest.parent, test_dest.name)

    def generate(self, res, target_dir, args=None):
        """Generate code for the OpenStackClient"""
        logging.debug("Generating OpenStackClient code in %s" % target_dir)
        osc_path = res.mod_name.split(".")[1:]

        context = dict(
            res=res.resource_class,
            sdk_mod_name=res.mod_name,
            osc_mod_name=res.mod_name.replace(
                "openstack.", "openstackclient."
            ),
            class_name=res.class_name,
            resource_name=res.class_name.lower(),
            sdk_service_name=res.service_name,
            proxy=res.proxy_obj,
            fqcn=res.fqcn,
            registry_name=res.registry_name,
            attrs=res.attrs,
        )

        work_dir = Path(target_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        # Generate common (i.e. formatters)
        impl_path = Path(work_dir, "openstackclient", "/".join(osc_path))
        impl_path.mkdir(parents=True, exist_ok=True)
        Path(impl_path, "__init__.py").touch()
        self._render(
            "osc/impl_common.py.j2",
            context,
            Path(work_dir, "openstackclient", "/".join(osc_path)),
            "common.py",
        )

        if res.resource_class.allow_list:
            # Generate methods for the list resources command
            self._render_command(
                context,
                osc_path,
                "osc/impl_list.py.j2",
                Path(
                    work_dir, "openstackclient", "/".join(osc_path), "list.py"
                ),
                "osc/test_unit_list.py.j2",
                Path(
                    work_dir,
                    "openstackclient",
                    "tests",
                    "unit",
                    "/".join(osc_path),
                    "test_list.py",
                ),
            )

        if res.resource_class.allow_fetch:
            # Generate methods for the GET resource command
            self._render_command(
                context,
                osc_path,
                "osc/impl_show.py.j2",
                Path(
                    work_dir, "openstackclient", "/".join(osc_path), "show.py"
                ),
                "osc/test_unit_show.py.j2",
                Path(
                    work_dir,
                    "openstackclient",
                    "tests",
                    "unit",
                    "/".join(osc_path),
                    "test_show.py",
                ),
            )

        if res.resource_class.allow_create:
            # Generate methods for the CREATE resource command
            self._render_command(
                context,
                osc_path,
                "osc/impl_create.py.j2",
                Path(
                    work_dir,
                    "openstackclient",
                    "/".join(osc_path),
                    "create.py",
                ),
                "osc/test_unit_create.py.j2",
                Path(
                    work_dir,
                    "openstackclient",
                    "tests",
                    "unit",
                    "/".join(osc_path),
                    "test_create.py",
                ),
            )

        if res.resource_class.allow_delete:
            # Generate methods for the DELETE resource command
            self._render_command(
                context,
                osc_path,
                "osc/impl_delete.py.j2",
                Path(
                    work_dir,
                    "openstackclient",
                    "/".join(osc_path),
                    "delete.py",
                ),
                "osc/test_unit_delete.py.j2",
                Path(
                    work_dir,
                    "openstackclient",
                    "tests",
                    "unit",
                    "/".join(osc_path),
                    "test_delete.py",
                ),
            )

        if res.resource_class.allow_commit:
            # Generate methods for the UPDATE resource command
            self._render_command(
                context,
                osc_path,
                "osc/impl_set.py.j2",
                Path(
                    work_dir,
                    "openstackclient",
                    "/".join(osc_path),
                    "set.py",
                ),
                "osc/test_unit_set.py.j2",
                Path(
                    work_dir,
                    "openstackclient",
                    "tests",
                    "unit",
                    "/".join(osc_path),
                    "test_set.py",
                ),
            )

            # Unset command
            self._render_command(
                context,
                osc_path,
                "osc/impl_unset.py.j2",
                Path(
                    work_dir,
                    "openstackclient",
                    "/".join(osc_path),
                    "unset.py",
                ),
                "osc/test_unit_unset.py.j2",
                Path(
                    work_dir,
                    "openstackclient",
                    "tests",
                    "unit",
                    "/".join(osc_path),
                    "test_unset.py",
                ),
            )

        # Format rendered code to have less flake complains. This will still
        # not guarantee code is fitting perfect, since there might be too long
        # lines
        self._format_code(
            Path(work_dir, "openstackclient", "/".join(osc_path)),
            Path(
                work_dir,
                "openstackclient",
                "tests",
                "unit",
                "/".join(osc_path),
            ),
        )
