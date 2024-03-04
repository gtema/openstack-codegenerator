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
from unittest import TestCase

from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from jinja2 import StrictUndefined

from codegenerator import base
from codegenerator import model
from codegenerator import rust_cli


class TestRustCliResponseManager(TestCase):
    def setUp(self):
        super().setUp()
        logging.basicConfig(level=logging.DEBUG)

    def test_parse_array_of_array_of_strings(self):
        expected_content = """
/// foo response representation
#[derive(Deserialize, Serialize)]
#[derive(Clone, StructTable)]
struct ResponseData {
    /// aoaos
    ///
    #[serde()]
    #[structable(pretty)]
    foo: Option<Value>,
}
        """
        schema = {
            "type": "object",
            "properties": {
                "foo": {
                    "type": ["array", "null"],
                    "description": "aoaos",
                    "items": {
                        "type": "array",
                        "description": "aos",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "uniqueItems": True,
                    },
                    "uniqueItems": True,
                }
            },
        }
        parser = model.OpenAPISchemaParser()
        (_, all_models) = parser.parse(schema)

        cli_rm = rust_cli.ResponseTypeManager()
        cli_rm.set_models(all_models)

        env = Environment(
            loader=FileSystemLoader("codegenerator/templates"),
            autoescape=select_autoescape(),
            undefined=StrictUndefined,
        )
        env.filters["wrap_markdown"] = base.wrap_markdown
        template = env.get_template("rust_cli/response_struct.j2")

        content = template.render(
            target_class_name="foo",
            response_type_manager=cli_rm,
            method=None,
            params={},
            is_json_patch=False,
            sdk_service_name="srv",
            resource_name="res",
            operation_type="dummy",
        )
        self.assertEqual(
            "".join([x.rstrip() for x in expected_content.split()]),
            "".join([x.rstrip() for x in content.split()]),
        )
