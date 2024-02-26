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
import mdformat as md

from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from jinja2 import StrictUndefined


def wrap_markdown(input: str, width: int = 79) -> str:
    """Apply mardownify to wrap the markdown"""
    return md.text(input, options={"wrap": width})


class BaseGenerator:
    def __init__(self):
        # Lower debug level of mdformat
        logging.getLogger("markdown_it").setLevel(logging.INFO)

        self.env = Environment(
            loader=FileSystemLoader("codegenerator/templates"),
            autoescape=select_autoescape(),
            undefined=StrictUndefined,
        )
        self.env.filters["wrap_markdown"] = wrap_markdown

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
        self, res, target_dir, openapi_spec=None, operation_id=None, args=None
    ):
        pass

    def generate_mod(
        self,
        target_dir,
        mod_path,
        mod_list: set[str],
        url: str,
        resouce_name: str,
        service_name: str,
    ):
        pass
