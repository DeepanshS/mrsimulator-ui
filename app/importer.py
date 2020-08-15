# -*- coding: utf-8 -*-
import base64
import json
import os
from urllib.request import urlopen

import csdmpy as cp
import dash_bootstrap_components as dbc
import dash_html_components as html
from csdmpy.dependent_variables.download import get_absolute_url_path
from dash import callback_context as ctx
from dash import no_update
from dash.dependencies import Input
from dash.dependencies import Output
from dash.dependencies import State
from dash.exceptions import PreventUpdate
from mrsimulator import Method
from mrsimulator import SpinSystem

from .app import app
from .custom_widgets import custom_button
from .custom_widgets import label_with_help_button
from .info import update_sample_info
from .nmr_method.utils import update_method_info
from .spin_system.utils import update_spin_system_info

__author__ = "Deepansh J. Srivastava"
__email__ = ["deepansh2012@gmail.com"]
PATH_ = os.path.split(__file__)[0]


def upload_data(prepend_id, message_for_URL, message_for_upload):
    """User uploaded files.
    Args:
        prepend_id: Prepends to the designated it.
    """

    # Method 2. From URL address
    # -------------------------------------------------------------------------
    data_from_url = html.Div(
        [
            label_with_help_button(
                *message_for_URL, id=f"upload-{prepend_id}-url-help"
            ),
            dbc.InputGroup(
                [
                    dbc.Input(
                        type="url",
                        id=f"upload-{prepend_id}-url",
                        value="",
                        placeholder="Paste URL ...",
                    ),
                    dbc.Button(
                        "Submit",
                        id=f"upload-{prepend_id}-url-submit",
                        className="append-last",
                    ),
                ]
            ),
        ],
        className="d-flex flex-column",
    )

    # presetting the fields for generating buttons
    fields = [
        {
            "text": "URL",
            "icon_classname": "fas fa-at",
            "id": f"upload-{prepend_id}-url-button",
            "tooltip": "Retrieve spin systems from a remote JSON file.",
            "active": False,
            "collapsable": data_from_url,
        }
    ]

    # Now generating buttons
    input_buttons = []
    for item in fields:
        input_buttons.append(
            custom_button(
                text=item["text"],
                icon_classname=item["icon_classname"],
                id=item["id"],
                tooltip=item["tooltip"],
                active=item["active"],
                outline=True,
                color="light",
            )
        )

    # Now wrapping from-url and upload-a-file input layouts in a collapsible widget
    input_layout_0 = []
    for item in fields:
        id_ = item["id"]
        input_layout_0.append(dbc.Collapse(item["collapsable"], id=f"{id_}-collapse"))

    input_layout = html.Div(
        [
            html.Div(
                dbc.Button(
                    html.I(className="fas fa-times"),
                    id=f"upload-{prepend_id}-panel-hide-button",
                    # color="dark",
                    size="sm",
                    style={"backgroundColor": "transparent", "outline": "none"},
                ),
                className="d-flex justify-content-end",
            ),
            # *addon,
            html.Div(
                [
                    dbc.ButtonGroup(input_buttons, vertical=True, className="button"),
                    dbc.Col(input_layout_0),
                ],
                className="d-flex justify-content-start",
            ),
        ],
        className="navbar-reveal",
    )

    # The input drawers are further wrapper as a collapsible. This collapsible widget
    # is activate from the navigation menu.
    drawer = dbc.Collapse(input_layout, id=f"upload-{prepend_id}-master-collapse")

    return drawer


spin_system_import_layout = upload_data(
    prepend_id="spin-system",
    message_for_URL=[
        "Enter URL of a JSON file containing the spin systems.",
        (
            "Spin systems file is a collection of sites and couplings ",
            "used in simulating NMR linshapes.",
        ),
    ],
    message_for_upload=[
        "Upload a JSON file containing the spin systems.",
        (
            "Spin systems file is a collection of sites and couplings ",
            "used in simulating NMR linshapes.",
        ),
    ],
)

spectrum_import_layout = upload_data(
    prepend_id="spectrum",
    message_for_URL=[
        "Enter URL of a CSDM compliant NMR data file.",
        "Add an NMR spectrum to compare with the simulation.",
    ],
    message_for_upload=[
        "Upload a CSDM compliant NMR data file.",
        "Add an NMR spectrum to compare with the simulation.",
    ],
)


# method
# Import or update the spin-systems.
@app.callback(
    [
        Output("alert-message-spin-system", "children"),
        Output("alert-message-spin-system", "is_open"),
        Output("local-spin-systems-data", "data"),
        Output("config", "data"),
        Output("spin-system-read-only", "children"),
        Output("method-read-only", "children"),
        Output("info-read-only", "children"),
    ],
    [
        # main page->drag and drop
        Input("upload-spin-system-local", "contents"),
        # from file->open
        Input("open-mrsimulator-file", "contents"),
        # spin-system->import+add
        Input("upload-and-add-spin-system-button", "contents"),
        # method->add measurement
        Input("import-measurement-for-method", "contents"),
        # graph->drag and drop
        Input("upload-from-graph", "contents"),
        Input("upload-spin-system-url-submit", "n_clicks"),
        # examples
        Input("selected-example", "value"),
        # when spin-system is modified
        Input("new-spin-system", "modified_timestamp"),
        # when method is modified
        Input("new-method", "modified_timestamp"),
        # spin-system->clear
        Input("confirm-clear-spin-system", "submit_n_clicks"),
        # method->clear
        Input("confirm-clear-methods", "submit_n_clicks"),
        # decompose into spin systems
        Input("decompose", "active"),
    ],
    [
        State("upload-spin-system-url", "value"),
        State("local-spin-systems-data", "data"),
        State("new-spin-system", "data"),
        State("new-method", "data"),
        State("select-method", "value"),
        State("decompose", "active"),
    ],
    prevent_initial_call=True,
)
def update_simulator(*args):
    """Update the local spin-systems when a new file is imported."""
    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print("trigger", trigger_id)

    existing_data = ctx.states["local-spin-systems-data.data"]

    # update the config of existing data
    decompose = "spin_system" if ctx.states["decompose.active"] else "none"
    if existing_data is not None:
        existing_data["config"]["decompose_spectrum"] = decompose

    no_updates = [no_update, no_update, no_update]
    if_error_occurred = [True, existing_data, *no_updates]

    # when decompose is triggered, return the updated existing data
    if trigger_id == "decompose":
        return ["", False, existing_data, no_update, *no_updates]

    # Add a new spin system object
    if trigger_id == "new-spin-system":
        new_spin_system = ctx.states["new-spin-system.data"]
        return modified_spin_system(existing_data, new_spin_system)

    # Add a new method object
    if trigger_id == "new-method":
        new_method = ctx.states["new-method.data"]
        return modified_method(existing_data, new_method)

    # Load a sample from pre-defined examples
    # The following section applies to when the spin-systems update is triggered from
    # set of pre-defined examples.
    if trigger_id == "selected-example":
        example = ctx.inputs["selected-example.value"]
        return example_selection(example, decompose)

    # Request and load a sample from URL
    # The following section applies to when the spin-systems update is triggered from
    # url-submit.
    if trigger_id == "upload-spin-system-url-submit":
        url = ctx.states("upload-spin-system-url.value")
        load_from_url(url, existing_data, decompose)

    if trigger_id == "confirm-clear-spin-system":
        return clear_system("spin_systems", existing_data)

    if trigger_id == "confirm-clear-methods":
        return clear_system("methods", existing_data)

    if trigger_id == "upload-and-add-spin-system-button":
        contents = ctx.inputs[f"{trigger_id}.contents"]
        if contents is None:
            raise PreventUpdate
        try:
            data = fix_missing_keys(parse_contents(contents))
        except Exception:
            message = "Error reading spin-systems."
            return [message, *if_error_occurred]
        data = parse_data(data, parse_method=False)
        existing_data["spin_systems"] += data["spin_systems"]
        return assemble_data(existing_data)

    # Load a sample from drag and drop
    # The following section applies to when the spin-systems update is triggered from
    # a user uploaded file.
    if trigger_id in ["upload-spin-system-local", "open-mrsimulator-file"]:
        contents = ctx.inputs[f"{trigger_id}.contents"]
        if contents is None:
            raise PreventUpdate
        try:
            data = fix_missing_keys(parse_contents(contents))
            data["config"]["decompose_spectrum"] = decompose
        except Exception:
            message = "Error reading spin-systems."
            return [message, *if_error_occurred]
        return assemble_data(parse_data(data))

    if trigger_id in ["import-measurement-for-method", "upload-from-graph"]:
        contents = ctx.inputs[f"{trigger_id}.contents"]
        content_string = contents.split(",")[1]
        decoded = base64.b64decode(content_string)
        success, exp_data, error_message = load_csdm(decoded)

        if not success:
            return [
                f"Error reading file. {error_message}",
                True,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            ]

        index = ctx.states["select-method.value"]
        method = existing_data["methods"][index]
        method["experiment"] = exp_data.to_dict()
        spectral_dim = method["spectral_dimensions"]
        for i, dim in enumerate(exp_data.dimensions):
            spectral_dim[i]["count"] = dim.count
            spectral_dim[i]["spectral_width"] = dim.count * dim.increment.to("Hz").value
            spectral_dim[i]["reference_offset"] = dim.coordinates_offset.to("Hz").value
            spectral_dim[i]["origin_offset"] = dim.origin_offset.to("Hz").value

        methods_info = update_method_info(existing_data["methods"])
        return ["", False, existing_data, no_update, no_update, methods_info, no_update]

    # Load a sample from drag and drop on the graph reqion
    # The following section applies to when the spin-systems update is triggered from
    # a user drag and drop on the graph.
    # if trigger_id == "upload-from-graph":
    #     if from_graph_content is None:
    #         raise PreventUpdate
    #     if from_graph_filename.split(".")[1] != "json":
    #         raise PreventUpdate
    #     try:
    #         data = parse_contents(from_graph_content, from_graph_filename)
    #     except Exception:
    #         message = "Error reading spin-systems."
    #         return [message, *if_error_occurred]

    #     return assemble_data(data)


def modified_method(existing_method_data, new_method):

    default = [no_update for _ in range(7)]
    if new_method is None:
        raise PreventUpdate

    index = new_method["index"]
    data = (
        existing_method_data
        if existing_method_data is not None
        else {"name": "", "description": "", "spin_systems": [], "methods": []}
    )
    method_data = new_method["data"]

    # Add a new method
    if new_method["operation"] == "add":
        data["methods"] += [method_data]
        methods_info = update_method_info(data["methods"])
        default[2], default[5] = data, methods_info
        return default

    # Modify a method
    if new_method["operation"] == "modify":
        if "experiment" in data["methods"][index]:
            method_data["experiment"] = data["methods"][index]["experiment"]
        data["methods"][index] = method_data
        methods_info = update_method_info(data["methods"])
        default[2], default[5] = data, methods_info
        return default

    # Duplicate a method
    if new_method["operation"] == "duplicate":
        data["methods"] += [method_data]
        methods_info = update_method_info(data["methods"])
        default[2], default[5] = data, methods_info
        return default

    # Delete a method
    if new_method["operation"] == "delete":
        if index is None:
            raise PreventUpdate
        del data["methods"][index]
        methods_info = update_method_info(data["methods"])
        default[2], default[5] = data, methods_info
        return default


def modified_spin_system(existing_data, new_spin_system):
    """Update the local spin-system data when an update is triggered."""
    config = {"is_new_data": False, "length_changed": False}
    default = [no_update for _ in range(7)]

    if new_spin_system is None:
        raise PreventUpdate
    index = new_spin_system["index"]
    data = (
        existing_data
        if existing_data is not None
        else {"name": "", "description": "", "spin_systems": [], "methods": []}
    )
    spin_system_data = new_spin_system["data"]
    # Modify spin-system
    # The following section applies to when the spin-systems update is triggered from
    # the GUI fields. This is a very common trigger, so we place it at the start.
    if new_spin_system["operation"] == "modify":
        data["spin_systems"][index] = spin_system_data
        config["index_last_modified"] = index

        spin_systems_info = update_spin_system_info(data["spin_systems"])
        default[2], default[3], default[4] = data, config, spin_systems_info
        return default

    # Add a new spin system
    # The following section applies to when the a new spin-systems is added from
    # add-spin-system-button.
    if new_spin_system["operation"] == "add":
        data["spin_systems"] += [spin_system_data]
        config["length_changed"] = True
        config["added"] = [site["isotope"] for site in spin_system_data["sites"]]
        config["index_last_modified"] = index

        spin_systems_info = update_spin_system_info(data["spin_systems"])
        default[2], default[3], default[4] = data, config, spin_systems_info
        return default

    # Copy an existing spin-system
    # The following section applies to when a request to duplicate the spin-systems
    # is initiated using the duplicate-spin-system-button.
    if new_spin_system["operation"] == "duplicate":
        data["spin_systems"] += [spin_system_data]
        config["length_changed"] = True
        config["added"] = [site["isotope"] for site in spin_system_data["sites"]]
        config["index_last_modified"] = index

        spin_systems_info = update_spin_system_info(data["spin_systems"])
        default[2], default[3], default[4] = data, config, spin_systems_info
        return default

    # Delete an spin-system
    # The following section applies to when a request to remove an spin-systems is
    # initiated using the remove-spin-system-button.
    if new_spin_system["operation"] == "delete":
        if index is None:
            raise PreventUpdate

        # the index to remove is given by spin_system_index
        config["removed"] = [
            site["isotope"] for site in data["spin_systems"][index]["sites"]
        ]
        del data["spin_systems"][index]
        config["index_last_modified"] = index

        spin_systems_info = update_spin_system_info(data["spin_systems"])
        default[2], default[3], default[4] = data, config, spin_systems_info
        return default


def example_selection(example, decompose):
    """Load the selected example."""
    if example in ["", None]:
        raise PreventUpdate
    response = urlopen(get_absolute_url_path(example, PATH_))
    data = fix_missing_keys(json.loads(response.read()))
    data["config"]["decompose_spectrum"] = decompose
    return assemble_data(parse_data(data))


def load_from_url(url, existing_data, decompose):
    """Load the selected data from url."""
    if url in ["", None]:
        raise PreventUpdate
    response = urlopen(url)
    try:
        data = fix_missing_keys(json.loads(response.read()))
        data["config"]["decompose_spectrum"] = decompose
        return assemble_data(parse_data(data))
    except Exception:
        no_updates = [no_update, no_update, no_update]
        if_error_occurred = [True, existing_data, *no_updates]
        message = "Error reading the file."
        return [message, *if_error_occurred]


def clear_system(attribute, existing_data):
    """Clear the list of spin-systems or methods

    Args:
        attribute: Enumeration with literals---`spin_systems` or `methods`
        existing_data: The existing simulator data and metadata.
    """
    if existing_data is None:
        raise PreventUpdate
    existing_data[attribute] = []
    return assemble_data(existing_data)


def fix_missing_keys(json_data):
    default_data = {
        "name": "Sample",
        "description": "Add a description ...",
        "spin_systems": [],
        "methods": [],
        "config": {},
    }
    data_keys = json_data.keys()
    for k in default_data.keys():
        if k not in data_keys:
            json_data[k] = default_data[k]
    return json_data


def parse_contents(contents):
    """Parse contents from the spin-systems file."""
    content_string = contents.split(",")[1]
    decoded = base64.b64decode(content_string)
    data = json.loads(str(decoded, encoding="UTF-8"))
    return data


def parse_data(data, parse_method=True, parse_spin_system=True):
    data_keys = data.keys()
    if parse_spin_system:
        if "spin_systems" in data_keys:
            a = [
                SpinSystem.parse_dict_with_units(_).dict() for _ in data["spin_systems"]
            ]
            data["spin_systems"] = [filter_dict(_) for _ in a]

    if parse_method:
        if "methods" in data_keys:
            a = [Method.parse_dict_with_units(_).dict() for _ in data["methods"]]
            # sim = [_["simulation"] for _ in a]
            # exp = [_["experiment"] for _ in a]
            data["methods"] = [filter_dict(_) for _ in a]
    return data


def assemble_data(data):
    config = {"is_new_data": True, "index_last_modified": 0, "length_changed": False}
    return [
        "",
        False,
        data,
        config,
        update_spin_system_info(data["spin_systems"]),
        update_method_info(data["methods"]),
        update_sample_info(data),
    ]


def filter_dict(dict1):
    dict_new = {}
    for key, val in dict1.items():
        if key in ["simulation", "property_units"] or val is None:
            continue

        if key == "isotope":
            dict_new[key] = val["symbol"]
            continue

        if key == "channels":
            dict_new[key] = [item["symbol"] for item in val]
            continue

        if key in ["experiment"]:
            dict_new[key] = val
            continue

        dict_new[key] = val
        if isinstance(val, dict):
            dict_new[key] = filter_dict(val)
        if isinstance(val, list):
            dict_new[key] = [filter_dict(_) if isinstance(_, dict) else _ for _ in val]

    return dict_new


# @app.callback(
#     [Output("isotope_id-0", "options"), Output("isotope_id-0", "value")],
#     [Input("local-spin-systems-data", "modified_timestamp")],
#     [State("local-spin-systems-data", "data"), State("isotope_id-0", "value")],
# )
# def update_dropdown_options(t, local_spin_system_data, old_isotope):
#     print("update_dropdown_options", old_isotope)
#     if local_spin_system_data is None:
#         raise PreventUpdate
#     if local_spin_system_data["spin_systems"] == []:
#         return [[], None]

#     # extracting a list of unique isotopes from the list of isotopes
#     isotopes = set(
#         [
#             site["isotope"]
#             for item in local_spin_system_data["spin_systems"]
#             for site in item["sites"]
#         ]
#     )
#     # Output isotope_id-0 -> options
#     # set up a list of options for the isotope dropdown menu
#     isotope_dropdown_options = [
#         {"label": site_iso, "value": site_iso} for site_iso in isotopes
#     ]

#     # Output isotope_id-0 -> value
#     # select an isotope from the list of options. If the previously selected isotope
#     # is in the new option list, use the previous isotope, else select the isotope at
#     # index zero of the options list.
#     isotope = (
#         old_isotope if old_isotope in isotopes else isotope_dropdown_options[0]
#               ["value"]
#     )

#     print(local_spin_system_data["spin_systems"])
#     # Output spin-system-dropdown -> options
#     # Update spin-system dropdown options base on local spin-systems data
#     # spin_system_dropdown_options = get_all_spin_system_dropdown_options(
#     #     local_spin_system_data["spin_systems"]
#     # )

#     return [
#         isotope_dropdown_options,
#         isotope,
#         # print_info(local_spin_system_data),
#     ]


# convert client-side function
@app.callback(
    Output("select-method", "options"),
    [Input("local-spin-systems-data", "data")],
    prevent_initial_call=True,
)
def update_list_of_methods(data):
    if data is None:
        raise PreventUpdate
    if data["methods"] is None:
        raise PreventUpdate
    options = [
        {"label": f'Method-{i} (Channel-{", ".join(k["channels"])})', "value": i}
        for i, k in enumerate(data["methods"])
    ]
    return options


# # Upload a CSDM compliant NMR data file.
# @app.callback(
#     [
#         Output("alert-message-spectrum", "children"),
#         Output("alert-message-spectrum", "is_open"),
#         Output("local-exp-external-data", "data"),
#     ],
#     [
#         # Input("upload-spectrum-local", "contents"),
#         Input("upload-from-graph", "contents"),
#         # Input("import-measurement-for-method", "contents"),
#     ],
#     [
#         # State("upload-spectrum-local", "filename"),
#         State("upload-from-graph", "filename"),
#         # State("import-measurement-for-method", "filename"),
#         State("local-exp-external-data", "data"),
#     ],
# )
# def update_exp_external_file(*args):
#     """Update a local CSDM file."""

#     if not ctx.triggered:
#         raise PreventUpdate

#     trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
#     content = ctx.inputs[f"{trigger_id}.contents"]
#     if content is None:
#         raise PreventUpdate

#     states = ctx.states

#     filename = states[f"{trigger_id}.filename"]
#     file_extension = filename.split(".")[1]
#     if file_extension not in ["csdf", "json"]:
#         return [f"Expecting a .csdf file, found .{file_extension}.", True, no_update]
#     if file_extension != "csdf":
#         raise PreventUpdate

#     # if trigger_id == "upload-spectrum-local":
#     #     content_string = csdm_upload_content
#     # if trigger_id == "upload-from-graph":
#     #     content_string = csdm_upload_content_graph

#     content = content.split(",")[1]
#     decoded = base64.b64decode(content)
#     success, data, error_message = load_csdm(decoded)
#     if success:
#         existing_data = states["local-exp-external-data.data"]
#         if existing_data is None:
#             existing_data = {}
#         existing_data["0"] = data.to_dict()
#         return ["", False, existing_data]
#     else:
#         return [f"Invalid JSON file. {error_message}", True, no_update]


def load_csdm(content):
    """Load a JSON file. Return a list with members
        - Success: True if file is read correctly,
        - Data: File content is success, otherwise an empty string,
        - message: An error message when JSON file load fails, else an empty string.
    """
    content = str(content, encoding="UTF-8")
    try:
        data = cp.loads(content)
        return True, data, ""
    except Exception as e:
        return False, "", e
