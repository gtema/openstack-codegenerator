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

from openstack.test.fakes import generate_fake_resource


class AnsibleGenerator(BaseGenerator):
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
        """Generate code for the Ansible"""
        logging.debug("Generating Ansible code in %s" % target_dir)
        ansible_path = ["plugins", "modules"]

        context = dict(
            res=res.resource_class,
            sdk_mod_name=res.mod_name,
            class_name=res.class_name,
            resource_name=res.class_name.lower(),
            sdk_service_name=res.service_name,
            proxy=res.proxy_obj,
            fqcn=res.fqcn,
            registry_name=res.registry_name,
            attrs=res.attrs,
            target_name=res.class_name.lower(),
        )
        if args and args.alternative_target_name:
            context["target_name"] = args.alternative_target_name
        context["ansible_module_name"] = "".join(
            [x.capitalize() for x in context["target_name"].split("_")]
        )

        work_dir = Path(target_dir, "ansible")

        # Generate fake resource to use in examples and tests
        fake_resource = generate_fake_resource(res.resource_class)
        context["fake_resource"] = fake_resource

        # Generate info module
        self._render(
            "ansible/impl_mod_info.py.j2",
            context,
            Path(work_dir, "/".join(ansible_path)),
            f"{context['target_name']}_info.py",
        )
        # Generate module
        self._render(
            "ansible/impl_mod.py.j2",
            context,
            Path(work_dir, "/".join(ansible_path)),
            f"{context['target_name']}.py",
        )
        # Generate ansible test role
        tests_dir = Path(work_dir, "ci/roles/", context["target_name"])
        self._render(
            "ansible/test_playbook.yaml.j2",
            context,
            Path(tests_dir, "ci/roles/", context["target_name"], "tasks"),
            "main.yaml",
        )
        # Format rendered code to have less flake complains. This will still
        # not guarantee code is fitting perfect, since there might be too long
        # lines
        self._format_code(
            Path(work_dir, "/".join(ansible_path)),
        )
