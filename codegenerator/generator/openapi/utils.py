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
import re

from bs4 import BeautifulSoup
from generator.common.schema import TypeSchema
from markdownify import markdownify as md
from ruamel.yaml.scalarstring import LiteralScalarString


def merge_api_ref_doc(
    openapi_spec, api_ref_src, allow_strip_version=True, doc_url_prefix=""
):
    """Merge infomation from rendered API-REF html into the spec

    :param openapi_spec: OpenAPI spec
    :param api_ref_src: path to the rendered API-REF
    :param bool allow_strip_version: Strip version prefix from the spec path if no direct match is found
    :param doc_ver_prefix: Use additional path prefix to find url match

    """
    with open(api_ref_src, "r") as fp:
        html_doc = fp.read()

    soup = BeautifulSoup(html_doc, "html.parser")
    docs_title = soup.find("div", class_="docs-title")
    title = None
    if docs_title:
        title = docs_title.find("h1").string
    main_body = soup.find("div", class_="docs-body")
    for section in main_body.children:
        if section.name != "section":
            continue
        section_id = section["id"]
        section_title = section.find("h1")

        if section_title.string:
            sec_title = section_title.string
        else:
            sec_title = list(section_title.strings)[0]
        sec_descr = md(str(section.p))
        if sec_title == title:
            openapi_spec.info["description"] = LiteralScalarString(sec_descr)
        else:
            for tag in openapi_spec.tags:
                if tag["name"] == section_id:
                    tag["description"] = LiteralScalarString(sec_descr)
                    # TODO(gtema): notes are aside of main "p" and not
                    # underneath
        # Iterate over URLs
        operation_url_containers = section.find_all(
            "div", class_="operation-grp"
        )
        for op in operation_url_containers:
            ep = op.find("div", class_="endpoint-container")
            ep_divs = ep.find_all("div")
            url = doc_url_prefix + "".join(ep_divs[0].strings)
            summary = "".join(ep_divs[1].strings)
            method_span = op.find("div", class_="operation").find(
                "span", class_="label"
            )
            method = method_span.string
            # Find operation
            path_spec = openapi_spec.paths.get(url)
            if (
                url not in openapi_spec.paths
                and url.startswith("/v")
                and allow_strip_version
            ):
                # There is no direct URL match, but doc URL starts with /vXX - try searching without version prefix
                m = re.search(r"^\/v[0-9.]*(\/.*)", url)
                if m.groups():
                    url = m.group(1)
                    path_spec = openapi_spec.paths.get(url)

            doc_source_param_mapping = {}
            if not path_spec:
                if "{" in url:
                    # The url contain parameters. It can be the case that
                    # parameter names are just different between source and
                    # docs
                    for existing_path in openapi_spec.paths.keys():
                        existing_path_parts = existing_path.split("/")
                        doc_url_parts = url.split("/")
                        if len(existing_path_parts) != len(doc_url_parts):
                            # Paths have different length. Skip
                            continue
                        is_search_aborted = False
                        for source, doc in zip(
                            existing_path_parts, doc_url_parts
                        ):
                            source_ = source.strip("{}")
                            doc_ = doc.strip("{}")
                            if (
                                source != doc
                                and source.startswith("{")
                                and doc.startswith("{")
                                and source_ != doc_
                            ):
                                # Path parameter on both sides. Consider renamed parameter
                                doc_source_param_mapping[doc_] = source_
                            elif source != doc:
                                # Path differs. No point in looking further
                                is_search_aborted = True
                                break
                        if is_search_aborted:
                            continue
                        # Assume we found something similar. Try to
                        # construct url with renames and compare it again.
                        # It should not be necessary, but it states: "safe is safe"
                        modified_url_parts = []
                        for part in url.split("/"):
                            if part.startswith("{"):
                                doc_param_name = part.strip("{}")
                                modified_url_parts.append(
                                    "{"
                                    + doc_source_param_mapping.get(
                                        doc_param_name, doc_param_name
                                    )
                                    + "}"
                                )
                            else:
                                modified_url_parts.append(part)
                        if "/".join(modified_url_parts) == existing_path:
                            # Is a definitive match
                            path_spec = openapi_spec.paths[existing_path]
                            break

            if not path_spec:
                logging.info("Cannot find path %s in the spec" % url)
                continue

            op_spec = getattr(path_spec, method.lower(), None)
            if not op_spec:
                logging.warn(
                    "Cannot find %s operation for %s in the spec"
                    % (method, url)
                )
                continue

            # Find the button in the operaion container to get ID of the
            # details section
            details_button = op.find("button")
            details_section_id = details_button["data-target"].strip("#")
            details_section = section.find("section", id=details_section_id)
            description = []
            action_name = None
            # Gather description section paragraphs to construct operation description
            for details_child in details_section.children:
                if details_child.name == "p":
                    description.append(str(details_child))

                elif details_child.name == "section":
                    if (
                        details_child.h3
                        and "Request" in details_child.h3.strings
                    ):
                        # Found request details
                        if not details_child.table:
                            logging.warn(
                                "No Parameters description table found for %s in html"
                                % url
                            )

                            continue
                        logging.debug(
                            "Processing Request parameters for %s" % url
                        )

                        spec_body = (
                            op_spec.requestBody.get("content", {})
                            .get("application/json", {})
                            .get("schema")
                        )
                        schema_specs = []
                        if not spec_body:
                            logging.debug(
                                "No request body present in the spec"
                            )
                            continue
                        if isinstance(spec_body, TypeSchema):
                            spec_body_ref = spec_body.ref
                            spec_body_oneOf = spec_body.oneOf
                        else:
                            spec_body_ref = spec_body.get("$ref")
                            spec_body_oneOf = spec_body.get("oneOf")
                        if spec_body_ref:
                            candidate_schema = (
                                openapi_spec.components.schemas.get(
                                    spec_body_ref.split("/")[-1]
                                )
                            )
                            oneOf = (
                                candidate_schema.oneOf
                                if isinstance(candidate_schema, TypeSchema)
                                else candidate_schema.oneOf
                            )
                            if oneOf:
                                for x in oneOf:
                                    if not x["$ref"]:
                                        continue
                                    schema_specs.append(
                                        openapi_spec.components.schemas.get(
                                            x["$ref"].split("/")[-1]
                                        )
                                    )
                            else:
                                schema_specs.append(candidate_schema)

                        elif spec_body_oneOf:
                            for x in spec_body_oneOf:
                                logging.debug(
                                    "Analyzing %s as an operation body candidate",
                                    x,
                                )
                                res = get_schema(openapi_spec, x)
                                if url.endswith("/action"):
                                    # For the actions we search for the
                                    # matching entity
                                    candidate_action_name = None
                                    if isinstance(res, TypeSchema):
                                        ext = res.openstack
                                    else:
                                        ext = res.get("x-openstack")
                                    if ext:
                                        candidate_action_name = ext.get(
                                            "action-name"
                                        )
                                    if not candidate_action_name:
                                        # Not able to figure out action name, abort
                                        continue

                                    if candidate_action_name and (
                                        candidate_action_name in summary
                                        or candidate_action_name
                                        in "".join(description)
                                    ):
                                        # This is an action we are hopefully interested in
                                        # Now we can have single schema or multiple (i.e. microversions)
                                        if isinstance(res, TypeSchema):
                                            itms = res.oneOf
                                        elif isinstance(res, dict):
                                            itms = res.get("oneOf")
                                        if itms:
                                            for itm in itms:
                                                schema_specs.append(
                                                    get_schema(
                                                        openapi_spec, itm
                                                    )
                                                )
                                        schema_specs.append(res)
                                        # Set the action name. Since
                                        # Request normally comes before
                                        # the response we can reuse it
                                        # later.
                                        action_name = candidate_action_name
                                        res.description = LiteralScalarString(
                                            md("".join(description))
                                        )

                                        break
                                else:
                                    # this is not an action, just add it to schemas
                                    schema_specs.append(res)
                        _doc_process_operation_table(
                            details_child.table.tbody,
                            openapi_spec,
                            op_spec,
                            schema_specs,
                            doc_source_param_mapping,
                        )
                    elif (
                        details_child.h3
                        and "Response" in details_child.h3.strings
                    ):
                        # Found response details
                        if not details_child.table:
                            logging.warn(
                                "No Parameters description table found for %s in html"
                                % url
                            )

                            continue
                        logging.debug(
                            "Processing Response parameters for %s" % url
                        )

                        spec_body = None
                        for rc in op_spec.responses:
                            # TODO(gtema): what if we have multiple positive RCs?
                            if rc.startswith("20"):
                                spec_body = (
                                    op_spec.responses[rc]
                                    .get("content", {})
                                    .get("application/json", {})
                                    .get("schema")
                                )
                        if not spec_body:
                            logging.info(
                                "Operation %s has no response bodyaccording to the spec",
                                op_spec.operationId,
                            )
                            continue
                        schema_specs = []
                        if isinstance(spec_body, TypeSchema):
                            ref = spec_body.ref
                            oneOf = spec_body.oneOf
                        else:
                            ref = spec_body.get("$ref")
                            oneOf = spec_body.get("oneOf")
                        if spec_body and ref:
                            candidate_schema = (
                                openapi_spec.components.schemas.get(
                                    ref.split("/")[-1]
                                )
                            )
                            if candidate_schema.oneOf:
                                for x in candidate_schema.oneOf:
                                    if not x.get("$ref"):
                                        continue
                                    schema_specs.append(
                                        openapi_spec.components.schemas.get(
                                            x["$ref"].split("/")[-1]
                                        )
                                    )
                            else:
                                schema_specs.append(candidate_schema)

                        elif spec_body and oneOf:
                            for x in oneOf:
                                res = get_schema(openapi_spec, x)

                                if url.endswith("/action"):
                                    # For the actions we search for the
                                    # matching entity
                                    candidate_action_name = None
                                    if isinstance(res, TypeSchema):
                                        ext = res.openstack
                                    else:
                                        ext = res.get("x-openstack")
                                    if ext:
                                        candidate_action_name = ext.get(
                                            "action-name"
                                        )
                                    if not candidate_action_name:
                                        # Not able to figure out action name, abort
                                        continue
                                    if candidate_action_name == action_name:
                                        schema_specs.append(res)

                                else:
                                    schema_specs.append(res)
                        _doc_process_operation_table(
                            details_child.table.tbody,
                            openapi_spec,
                            op_spec,
                            schema_specs,
                            doc_source_param_mapping,
                        )

            if not url.endswith("/action"):
                pass
                # This is not an "action" which combines various
                # operations, so no summary/description info
                op_spec.summary = summary
                op_spec.description = LiteralScalarString(
                    md("".join(description))
                )


def _doc_process_operation_table(
    tbody,
    openapi_spec,
    op_spec,
    schema_specs,
    doc_source_param_mapping,
):
    """Process DOC table (Request/Reseponse) and try to set description to
    the matching schema property"""

    for row in tbody.find_all("tr"):
        tds = row.find_all("td")
        doc_param_name = tds[0].p.string.replace(" (Optional)", "")
        doc_param_location = tds[1].p.string
        # doc_param_type = tds[2].p.string
        doc_param_descr = md("".join(str(x) for x in tds[3].contents)).strip(
            "\n "
        )
        if doc_param_location in ["query", "header", "path"]:
            for src_param in op_spec.parameters:
                if src_param.ref:
                    pname = src_param.ref.split("/")[-1]
                    param_def = openapi_spec.components.parameters[
                        doc_source_param_mapping.get(pname, pname)
                    ]
                else:
                    param_def = src_param

                if (
                    param_def.location == doc_param_location
                    and param_def.name == doc_param_name
                ):
                    param_def.description = LiteralScalarString(
                        doc_param_descr
                    )
        elif doc_param_location == "body":
            # Body param. Traverse through body information
            for schema in schema_specs:
                prop = _find_schema_property(schema, doc_param_name)
                if prop:
                    if hasattr(prop, "description"):
                        prop.description = LiteralScalarString(doc_param_descr)
                    else:
                        prop["description"] = LiteralScalarString(
                            doc_param_descr
                        )
            pass


def _find_schema_property(schema, target_prop_name):
    if not schema:
        return
    # logging.debug("Searching %s in %s", target_prop_name, schema)
    xtype = schema["type"] if isinstance(schema, dict) else schema.type
    if xtype == "object":
        if isinstance(schema, TypeSchema):
            props = schema.properties
        elif isinstance(schema, dict):
            props = schema.get("properties", {})
        if not props:
            return
        for prop_name, prop_def in props.items():
            prop_type = (
                prop_def.get("type")
                if isinstance(prop_def, dict)
                else prop_def.type
            )
            if prop_name == target_prop_name:
                return prop_def
            elif (
                "." in target_prop_name
                and target_prop_name.startswith(prop_name)
                and prop_type == "object"
            ):
                # block_device_mappingg_v2.tag like pattern
                candidate = _find_schema_property(
                    prop_def, target_prop_name[len(prop_name) + 1 :]
                )
                if candidate:
                    return candidate
            elif prop_type == "object":
                # name under the "server"
                candidate = _find_schema_property(prop_def, target_prop_name)
                if candidate:
                    return candidate
            elif prop_type == "array":
                # name under the "server"
                candidate = _find_schema_property(
                    prop_def.get("items")
                    if isinstance(prop_def, dict)
                    else prop_def.items,
                    target_prop_name,
                )
                if candidate:
                    return candidate

    elif xtype == "array":
        items_schema = (
            schema.items
            if isinstance(schema, TypeSchema)
            else schema.get("items")
        )
        candidate = _find_schema_property(items_schema, target_prop_name)
        if candidate:
            return candidate


def get_schema(openapi_spec, ref):
    """Resolve schema reference"""
    if isinstance(ref, TypeSchema):
        xref = ref.ref
    elif isinstance(ref, str):
        xref = ref
    elif isinstance(ref, dict):
        xref = ref.get("$ref")
    if xref:
        return openapi_spec.components.schemas.get(xref.split("/")[-1])
    else:
        return ref
