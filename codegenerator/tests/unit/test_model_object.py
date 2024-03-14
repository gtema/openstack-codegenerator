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
from unittest import TestCase

from codegenerator import model


class TestParserObject(TestCase):
    """Test parsing of the `object`"""

    def setUp(self):
        super().setUp()
        self.parser = model.OpenAPISchemaParser()

    def test_parse_props(self):
        schema = {"type": "object", "properties": {"foo": {"type": "string"}}}
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.Struct(
                fields={
                    "foo": model.StructField(
                        data_type=model.ConstraintString()
                    )
                }
            ),
            res,
        )
        self.assertEqual(1, len(all))

    def test_parse_props_additional_props_forbidden(self):
        schema = {
            "type": "object",
            "properties": {
                "foo": {"type": "string"},
            },
            "additionalProperties": False,
        }
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.Struct(
                fields={
                    "foo": model.StructField(
                        data_type=model.ConstraintString()
                    )
                }
            ),
            res,
        )
        self.assertEqual(1, len(all))

    def test_parse_props_additional_props_allowed(self):
        schema = {
            "type": "object",
            "properties": {
                "foo": {"type": "string"},
            },
            "additionalProperties": True,
        }
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.Struct(
                fields={
                    "foo": model.StructField(
                        data_type=model.ConstraintString()
                    )
                },
                additional_fields=model.PrimitiveAny(),
            ),
            res,
        )
        self.assertEqual(1, len(all))

    def test_parse_props_additional_props_type(self):
        schema = {
            "type": "object",
            "properties": {
                "foo": {"type": "string"},
            },
            "additionalProperties": {"type": "string"},
        }
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.Struct(
                fields={
                    "foo": model.StructField(
                        data_type=model.ConstraintString()
                    )
                },
                additional_fields=model.ConstraintString(),
            ),
            res,
        )
        self.assertEqual(1, len(all))

    def test_parse_only_additional_props(self):
        schema = {
            "type": "object",
            "additionalProperties": {"type": "string"},
        }
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.Dictionary(value_type=model.ConstraintString()),
            res,
        )
        self.assertEqual(1, len(all))

    def test_parse_additional_props_object(self):
        schema = {
            "type": "object",
            "description": "foo schema",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "foo": {"type": "string", "description": "foo field"},
                    "bar": {"type": "number", "description": "bar field"},
                },
            },
        }
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.Dictionary(
                description="foo schema",
                value_type=model.Struct(
                    fields={
                        "foo": model.StructField(
                            data_type=model.ConstraintString(),
                            description="foo field",
                        ),
                        "bar": model.StructField(
                            data_type=model.ConstraintNumber(),
                            description="bar field",
                        ),
                    }
                ),
            ),
            res,
        )
        self.assertEqual(2, len(all))

    def test_parse_props_required(self):
        schema = {
            "type": "object",
            "properties": {
                "foo": {"type": "string"},
                "bar": {"type": "number"},
            },
            "required": ["foo"],
        }
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.Struct(
                fields={
                    "foo": model.StructField(
                        data_type=model.ConstraintString(), is_required=True
                    ),
                    "bar": model.StructField(
                        data_type=model.ConstraintNumber(), is_required=False
                    ),
                }
            ),
            res,
        )
        self.assertEqual(1, len(all))

    def test_parse_props_required_oneOf(self):
        schema = {
            "type": "object",
            "properties": {
                "foo": {"type": "string"},
                "bar": {"type": "number"},
            },
            "oneOf": [{"required": ["foo"]}, {"required": ["bar"]}],
        }
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.Struct(
                fields={
                    "foo": model.StructField(
                        data_type=model.ConstraintString(), is_required=False
                    ),
                    "bar": model.StructField(
                        data_type=model.ConstraintNumber(), is_required=False
                    ),
                }
            ),
            res,
        )
        self.assertEqual(1, len(all))

    def test_parse_pattern_props(self):
        schema = {
            "type": "object",
            "properties": {
                "foo": {"type": "string"},
            },
            "patternProperties": {"^A": {"type": "string"}},
        }
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.Struct(
                fields={
                    "foo": model.StructField(
                        data_type=model.ConstraintString()
                    )
                },
                pattern_properties={
                    "^A": model.ConstraintString(),
                },
            ),
            res,
        )
        self.assertEqual(1, len(all))

    def test_parse_only_pattern_props(self):
        schema = {
            "type": "object",
            "patternProperties": {"^A": {"type": "string"}},
        }
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.Dictionary(value_type=model.ConstraintString()),
            res,
        )
        self.assertEqual(1, len(all))

    def test_parse_empty(self):
        schema = {
            "type": "object",
        }
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.Dictionary(value_type=model.PrimitiveAny()),
            res,
        )
        self.assertEqual(1, len(all))

    def test_parse_oneOf(self):
        schema = {
            "type": "object",
            "oneOf": [
                {
                    "properties": {
                        "foo": {"type": "string"},
                    }
                },
                {
                    "properties": {
                        "bar": {"type": "string"},
                    }
                },
            ],
        }
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.OneOfType(
                kinds=[
                    model.Struct(
                        fields={
                            "foo": model.StructField(
                                data_type=model.ConstraintString()
                            )
                        },
                    ),
                    model.Struct(
                        fields={
                            "bar": model.StructField(
                                data_type=model.ConstraintString()
                            )
                        },
                    ),
                ]
            ),
            res,
        )
        # Struct themselves are now also separate models
        self.assertEqual(3, len(all))

    def test_parse_allOf(self):
        schema = {
            "type": "object",
            "allOf": [
                {
                    "properties": {
                        "foo": {"type": "string"},
                    }
                },
                {
                    "properties": {
                        "foo": {"type": "string"},
                        "bar": {"type": "string"},
                    },
                    "required": ["foo"],
                },
            ],
        }
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.Struct(
                fields={
                    "foo": model.StructField(
                        data_type=model.ConstraintString(), is_required=True
                    ),
                    "bar": model.StructField(
                        data_type=model.ConstraintString()
                    ),
                },
            ),
            res,
        )
        self.assertEqual(1, len(all))

    def test_parse_props_descriptions(self):
        schema = {
            "type": "object",
            "description": "foo schema",
            "properties": {
                "foo": {"type": "string", "description": "foo field"},
                "bar": {"type": "number", "description": "bar field"},
            },
        }
        (res, all) = self.parser.parse(schema)
        self.assertEqual(
            model.Struct(
                description="foo schema",
                fields={
                    "foo": model.StructField(
                        data_type=model.ConstraintString(),
                        description="foo field",
                    ),
                    "bar": model.StructField(
                        data_type=model.ConstraintNumber(),
                        description="bar field",
                    ),
                },
            ),
            res,
        )
        self.assertEqual(1, len(all))
