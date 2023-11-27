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

import abc
import logging
from pathlib import Path
import subprocess

from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from jinja2 import StrictUndefined


class BaseGenerator:
    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader("codegenerator/generator/templates"),
            autoescape=select_autoescape(),
            undefined=StrictUndefined,
        )

    def get_parser(self, parser):
        return parser

    def _render(self, template, context, dest, fname):
        """Render single template"""
        template = self.env.get_template(template)
        content = template.render(**context)
        dest.mkdir(parents=True, exist_ok=True)
        with open(Path(dest, fname), "w") as fp:
            logging.debug("Writing %s" % (fp.name))
            fp.write(content)

    def _format_code(self, *args):
        """Format code using Black

        :param *args: Path to the code to format
        """
        for path in args:
            subprocess.run(["black", "-l", "79", path])

    @abc.abstractmethod
    def generate(
        self, res, target_dir, spec=None, operation_id=None, args=None
    ):
        pass
