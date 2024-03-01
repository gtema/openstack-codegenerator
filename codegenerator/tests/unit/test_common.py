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
from unittest import TestCase

from typing import Any

from codegenerator import common


class TestFindResponseSchema(TestCase):
    FOO = {"foo": {"type": "string"}}

    # def setUp(self):
    #     super().setUp()
    #     logging.basicConfig(level=logging.DEBUG)

    def test_find_with_single_candidate(self):
        responses = {
            "200": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {**self.FOO},
                        }
                    }
                }
            }
        }
        self.assertEqual(
            responses["200"]["content"]["application/json"]["schema"],
            common.find_response_schema(responses, "foo"),
        )

    def test_find_with_list(self):
        responses = {
            "200": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "foos": {"type": "array", "items": self.FOO}
                            },
                        }
                    }
                }
            }
        }
        self.assertEqual(
            responses["200"]["content"]["application/json"]["schema"],
            common.find_response_schema(responses, "foo"),
        )

    def test_find_correct_action(self):
        foo_action = {
            "type": "string",
            "x-openstack": {"action-name": "foo-action"},
        }
        bar_action = {
            "type": "string",
            "x-openstack": {"action-name": "bar-action"},
        }
        responses: dict[str, Any] = {
            "200": {
                "content": {
                    "application/json": {
                        "schema": {"type": "object", "properties": self.FOO}
                    }
                }
            },
            "204": {
                "content": {
                    "application/json": {
                        "schema": {"oneOf": [foo_action, bar_action]}
                    }
                }
            },
        }
        self.assertEqual(
            foo_action,
            common.find_response_schema(responses, "foo", "foo-action"),
        )
        self.assertEqual(
            bar_action,
            common.find_response_schema(responses, "foo", "bar-action"),
        )
        self.assertIsNone(
            common.find_response_schema(responses, "foo", "baz-action"),
        )
        self.assertEqual(
            responses["200"]["content"]["application/json"]["schema"],
            common.find_response_schema(responses, "foo"),
        )

    def test_no_candidates_returns_root(self):
        responses = {
            "200": {
                "content": {
                    "application/json": {
                        "schema": self.FOO["foo"],
                    }
                }
            }
        }
        self.assertEqual(
            responses["200"]["content"]["application/json"]["schema"],
            common.find_response_schema(responses, "foo"),
        )

    def test_plural(self):
        map = {
            "policy": "policies",
            "server": "servers",
            "access": "accesses",
            "bus": "buses",
            "box": "boxes",
            "buzz": "buzzes",
            "wish": "wishes",
            "clash": "clashes",
            "potato": "potatoes",
            "axis": "axes",
            "elf": "elves",
            "knife": "knives",
        }
        for singular, plural in map.items():
            self.assertEqual(plural, common.get_plural_form(singular))

    def test_singular(self):
        map = {
            "policy": "policies",
            "server": "servers",
            "access": "accesses",
            "bus": "buses",
            "box": "boxes",
            "buzz": "buzzes",
            "wish": "wishes",
            "clash": "clashes",
            "potato": "potatoes",
        }
        for singular, plural in map.items():
            self.assertEqual(singular, common.get_singular_form(plural))
