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
from codegenerator import rust_sdk
from codegenerator.common import rust as common_rust
from codegenerator.tests.unit import test_model


class TestRustSdkModel(TestCase):
    models = [
        model.Struct(
            reference=None,
            fields={
                "a": model.StructField(
                    data_type=model.PrimitiveString(),
                    description="a descr",
                    is_required=True,
                ),
                "b": model.StructField(
                    data_type=model.ConstraintString(
                        format="foo", minLength=1, maxLength=2, pattern="3"
                    )
                ),
                "c": model.StructField(
                    data_type=model.ConstraintNumber(format="double")
                ),
                "d": model.StructField(data_type=model.ConstraintInteger()),
                "e": model.StructField(data_type=model.PrimitiveBoolean()),
                "f": model.StructField(
                    data_type=model.Reference(name="f", type=model.OneOfType),
                    is_required=True,
                ),
                "g": model.StructField(
                    data_type=model.Dictionary(
                        value_type=model.PrimitiveString(),
                    )
                ),
            },
        ),
        model.OneOfType(
            reference=model.Reference(name="f", type=model.OneOfType),
            kinds=[
                model.PrimitiveString(),
                model.Reference(name="f_array", type=model.Array),
            ],
        ),
        model.Array(
            reference=model.Reference(name="f_array", type=model.Array),
            item_type=model.PrimitiveString(),
        ),
    ]

    #    def test_string_type(self):
    #        # generator = rust_sdk.Generator()
    #        res = rust_sdk.get_type(model.PrimitiveString())
    #        self.assertIsInstance(res, rust_sdk.String)
    #        self.assertEqual(res.type_hint, "Cow<'a, str>")
    #        self.assertEqual(res.imports, set(["std::borrow::Cow"]))

    def test_model_string_vec_strings(self):
        """Ensure oneOf from vec<string> and string is mapped to vec<string>"""
        logging.basicConfig(level=logging.DEBUG)
        type_manager = rust_sdk.TypeManager()
        type_manager.set_models(self.models)
        mod = type_manager.convert_model(
            model.Reference(name="f", type=model.OneOfType)
        )
        self.assertIsInstance(mod, common_rust.Array)
        self.assertIsInstance(mod.item_type, rust_sdk.String)
        # print(type_manager.refs)

    def test_model_struct(self):
        logging.basicConfig(level=logging.DEBUG)
        type_manager = rust_sdk.TypeManager()
        type_manager.set_models(self.models)
        mod = type_manager.convert_model(self.models[0])
        self.assertIsInstance(mod, rust_sdk.Struct)
        self.assertFalse(mod.fields["a"].is_optional)
        field_a = mod.fields["a"]
        self.assertEqual(field_a.is_optional, False)
        self.assertEqual(field_a.description, "a descr")
        self.assertEqual(field_a.type_hint, "Cow<'a, str>")
        field_b = mod.fields["b"]
        self.assertEqual(field_b.is_optional, True)
        self.assertEqual(field_b.type_hint, "Option<Cow<'a, str>>")
        field_c = mod.fields["c"]
        self.assertEqual(field_c.is_optional, True)
        self.assertEqual(field_c.type_hint, "Option<f64>")
        field_d = mod.fields["d"]
        self.assertEqual(field_d.is_optional, True)
        self.assertEqual(field_d.type_hint, "Option<i32>")
        field_d = mod.fields["d"]
        field_e = mod.fields["e"]
        self.assertEqual(field_e.is_optional, True)
        self.assertEqual(field_e.type_hint, "Option<bool>")
        field_f = mod.fields["f"]
        self.assertEqual(field_f.is_optional, False)
        self.assertEqual(field_f.type_hint, "Vec<Cow<'a, str>>")
        field = mod.fields["g"]
        self.assertEqual(field.is_optional, True)
        self.assertEqual(
            field.type_hint, "Option<BTreeMap<Cow<'a, str>, Cow<'a, str>>>"
        )
        self.assertEqual(set(["'a"]), mod.lifetimes)

    def test_get_submodels(self):
        logging.basicConfig(level=logging.DEBUG)
        type_manager = rust_sdk.TypeManager()
        type_manager.set_models(test_model.EXPECTED_DATA_TYPES)
        # res = type_manager.get_subtypes()
        self.assertEqual(
            set(
                [
                    "std::collections::BTreeMap",
                    "std::borrow::Cow",
                    "serde::Deserialize",
                    "serde::Serialize",
                    "serde_json::Value",
                ]
            ),
            type_manager.get_imports(),
        )

    def test_render_submodels(self):
        # expected_subtypes_render = ""
        logging.basicConfig(level=logging.DEBUG)
        type_manager = rust_sdk.TypeManager()
        type_manager.set_models(test_model.EXPECTED_DATA_TYPES)
        env = Environment(
            loader=FileSystemLoader("codegenerator/templates"),
            autoescape=select_autoescape(),
            undefined=StrictUndefined,
        )
        env.filters["wrap_markdown"] = base.wrap_markdown

        template = env.get_template("rust_sdk/subtypes.j2")
        content = template.render(type_manager=type_manager)

        # TODO: implement proper rendering with individual model types
        self.assertIsNotNone(content)

        # self.assertEqual(
        #     "".join([x.rstrip() for x in expected_subtypes_render.split()]),
        #     "".join([x.rstrip() for x in content.split()]),
        # )

    def test_render_root_type(self):
        expected_root_render = """
#[derive(Builder, Debug, Clone)]
#[builder(setter(strip_option))]
pub struct Request<'a> {
    #[builder(default, setter(into))]
    pub(crate) os_sch_hnt_scheduler_hints: Option<OsSchHntSchedulerHints<'a>>,

    /// scheduler hints description
    ///
    #[builder(default, setter(into))]
    pub(crate) os_scheduler_hints: Option<OsSchedulerHints<'a>>,

    /// A `server` object.
    ///
    #[builder(setter(into))]
    pub(crate) server: Server<'a>,

    #[builder(setter(name = "_headers"), default, private)]
    _headers: Option<HeaderMap>,
}
        """
        logging.basicConfig(level=logging.DEBUG)
        type_manager = rust_sdk.TypeManager()
        type_manager.set_models(test_model.EXPECTED_DATA_TYPES)
        env = Environment(
            loader=FileSystemLoader("codegenerator/templates"),
            autoescape=select_autoescape(),
            undefined=StrictUndefined,
        )
        env.filters["wrap_markdown"] = base.wrap_markdown

        template = env.get_template("rust_sdk/request_struct.j2")
        content = template.render(
            type_manager=type_manager,
            method=None,
            params={},
            is_json_patch=False,
        )

        self.assertEqual(
            "".join([x.rstrip() for x in expected_root_render.split()]),
            "".join([x.rstrip() for x in content.split()]),
        )
