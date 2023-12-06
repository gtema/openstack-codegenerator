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


from codegenerator import model
from codegenerator import rust_sdk
from codegenerator.tests.unit import test_model


class TestRustSdkModel(TestCase):
    models = [
        model.Struct(
            reference=model.Reference(name="Root", type=model.Struct),
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

    def test_string_type(self):
        # generator = rust_sdk.Generator()
        res = rust_sdk.get_type(model.PrimitiveString())
        self.assertIsInstance(res, rust_sdk.String)
        self.assertEqual(res.type_hint, "Cow<'a, str>")
        self.assertEqual(res.imports, set(["std::borrow::Cow"]))

    def test_model_string_vec_strings(self):
        """Ensure oneOf from vec<string> and string is mapped to vec<string>"""
        logging.basicConfig(level=logging.DEBUG)
        type_manager = rust_sdk.TypeManager()
        type_manager.set_models(self.models)
        mod = type_manager.get_dst_type(
            model.Reference(name="f", type=model.OneOfType)
        )
        self.assertIsInstance(mod, rust_sdk.Array)
        self.assertIsInstance(mod.item_type, rust_sdk.String)
        # print(type_manager.refs)

    def test_model_struct(self):
        logging.basicConfig(level=logging.DEBUG)
        type_manager = rust_sdk.TypeManager()
        type_manager.set_models(self.models)
        mod = type_manager.get_dst_type(
            model.Reference(name="Root", type=model.Struct)
        )
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
                    "serde_json::Value",
                    "std::borrow::Cow",
                ]
            ),
            type_manager.get_imports(),
        )

    def test_render_submodels(self):
        expected_subtypes_render = """

[derive(Debug, Deserialize, Clone, Serialize)]
struct Networks<'a> {
    #[serde(skip_serializing_if="Option::is_none")]
    fixed_ip: Option<Cow<'a, str>>,

    port: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    uuid: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    tag: Option<Cow<'a, str>>,
}

[derive(Debug, Deserialize, Clone, Serialize)]
enum NetworksEnum<'a> {
    F1(Vec<Networks>),
    F2(Cow<'a, str>),
}

[derive(Debug, Deserialize, Clone, Serialize)]
struct BlockDeviceMapping<'a> {
    #[serde(skip_serializing_if="Option::is_none")]
    virtual_name: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    volume_id: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    snapshot_id: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    volume_size: Option<i32>,
    #[serde(skip_serializing_if="Option::is_none")]
    device_name: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    delete_on_termination: Option<bool>,
    #[serde(skip_serializing_if="Option::is_none")]
    no_device: Option<None::<String>>,
    #[serde(skip_serializing_if="Option::is_none")]
    connection_info: Option<Cow<'a, str>>,
}

[derive(Debug, Deserialize, Clone, Serialize)]
struct BlockDeviceMappingV2<'a> {
    #[serde(skip_serializing_if="Option::is_none")]
    virtual_name: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    volume_id: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    snapshot_id: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    volume_size: Option<i32>,
    #[serde(skip_serializing_if="Option::is_none")]
    device_name: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    delete_on_termination: Option<bool>,
    #[serde(skip_serializing_if="Option::is_none")]
    no_device: Option<None::<String>>,
    #[serde(skip_serializing_if="Option::is_none")]
    connection_info: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    source_type: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    uuid: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    image_id: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    destination_type: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    guest_format: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    device_type: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    disk_bus: Option<Cow<'a, str>>,

    boot_index: Option<i32>,
    #[serde(skip_serializing_if="Option::is_none")]
    tag: Option<Cow<'a, str>>,

    volume_type: Option<Cow<'a, str>>,
}

[derive(Debug, Deserialize, Clone, Serialize)]
struct SecurityGroups<'a> {

    /// A target cell name. Schedule the server in a host in the cell
    /// specified.
    #[serde(skip_serializing_if="Option::is_none")]
    name: Option<Cow<'a, str>>,
}

/// A `server` object.
[derive(Debug, Deserialize, Clone, Serialize)]
struct Server<'a> {

    /// dummy description
    #[serde(skip_serializing_if="Option::is_none")]
    name: Cow<'a, str>,
    #[serde(skip_serializing_if="Option::is_none")]
    imageref: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    flavorref: i32,
    #[serde(skip_serializing_if="Option::is_none")]
    adminpass: Option<Cow<'a, str>>,

    /// metadata description
    #[serde(skip_serializing_if="Option::is_none")]
    metadata: Option<BTreeMap<Cow<'a, str>, Cow<'a, str>>>,

    /// Networks description
    #[serde(skip_serializing_if="Option::is_none")]
    networks: NetworksEnum,

    /// DiskConfig description
    #[serde(skip_serializing_if="Option::is_none")]
    os_dcf_diskconfig: Option<Cow<'a, str>>,

    /// IPv4 address
    #[serde(skip_serializing_if="Option::is_none")]
    accessipv4: Option<Cow<'a, str>>,

    /// A target cell name.
    #[serde(skip_serializing_if="Option::is_none")]
    availability_zone: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    block_device_mapping: Option<Vec<BlockDeviceMapping>>,

    /// descr
    #[serde(skip_serializing_if="Option::is_none")]
    block_device_mapping_v2: Option<Vec<BlockDeviceMappingV2>>,
    #[serde(skip_serializing_if="Option::is_none")]
    config_drive: Option<bool>,
    #[serde(skip_serializing_if="Option::is_none")]
    min_count: Option<i32>,

    /// SG descr
    #[serde(skip_serializing_if="Option::is_none")]
    security_groups: Option<Vec<SecurityGroups>>,

    /// user data
    #[serde(skip_serializing_if="Option::is_none")]
    user_data: Option<Cow<'a, str>>,

    description: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    tags: Option<Vec<Cow<'a, str>>>,

    trusted_image_certificates: Option<Vec<Cow<'a, str>>>,
    #[serde(skip_serializing_if="Option::is_none")]
    host: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    hypervisor_hostname: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    hostname: Option<Cow<'a, str>>,
}

[derive(Debug, Deserialize, Clone, Serialize)]
enum Query<'a> {
    F1(Cow<'a, str>),
    F2(BTreeMap<Cow<'a, str>, Value>),
}

/// scheduler hints description
[derive(Debug, Deserialize, Clone, Serialize)]
struct OsSchedulerHints<'a> {
    #[serde(skip_serializing_if="Option::is_none")]
    group: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    different_host: Option<Vec<Cow<'a, str>>>,

    /// A list of server UUIDs or a server UUID.
    #[serde(skip_serializing_if="Option::is_none")]
    same_host: Option<Vec<Cow<'a, str>>>,
    #[serde(skip_serializing_if="Option::is_none")]
    query: Option<Query>,
    #[serde(skip_serializing_if="Option::is_none")]
    target_cell: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    different_cell: Option<Vec<Cow<'a, str>>>,

    /// Schedule the server on a host in the network specified with
    #[serde(skip_serializing_if="Option::is_none")]
    build_near_host_ip: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    cidr: Option<Cow<'a, str>>,
}

[derive(Debug, Deserialize, Clone, Serialize)]
struct OsSchHntSchedulerHints<'a> {
    #[serde(skip_serializing_if="Option::is_none")]
    group: Option<Cow<'a, str>>,

    /// A list of server UUIDs or a server UUID.
    /// Schedule the server on a different host from a set of servers.
    /// It is available when `DifferentHostFilter` is available on cloud side.
    #[serde(skip_serializing_if="Option::is_none")]
    different_host: Option<Vec<Cow<'a, str>>>,
    #[serde(skip_serializing_if="Option::is_none")]
    same_host: Option<Vec<Cow<'a, str>>>,
    #[serde(skip_serializing_if="Option::is_none")]
    query: Option<Query>,
    #[serde(skip_serializing_if="Option::is_none")]
    target_cell: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    different_cell: Option<Vec<Cow<'a, str>>>,
    #[serde(skip_serializing_if="Option::is_none")]
    build_near_host_ip: Option<Cow<'a, str>>,
    #[serde(skip_serializing_if="Option::is_none")]
    cidr: Option<Cow<'a, str>>,
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

        template = env.get_template("rust_sdk/subtypes.j2")
        content = template.render(type_manager=type_manager)

        # print(content)
        self.assertEqual(
            "".join([x.rstrip() for x in expected_subtypes_render.split()]),
            "".join([x.rstrip() for x in content.split()]),
        )

    def test_render_root_type(self):
        logging.basicConfig(level=logging.DEBUG)
        type_manager = rust_sdk.TypeManager()
        type_manager.set_models(test_model.EXPECTED_DATA_TYPES)
        env = Environment(
            loader=FileSystemLoader("codegenerator/templates"),
            autoescape=select_autoescape(),
            undefined=StrictUndefined,
        )

        template = env.get_template("rust_sdk/root_struct.j2")
        content = template.render(
            type_manager=type_manager, method=None, params={}
        )

        self.assertIsNotNone(content)
        # print(content)
        # self.assertEqual(
        #    "".join([x.rstrip() for x in expected_subtypes_render.split()]),
        #    "".join([x.rstrip() for x in content.split()]),
        # )
