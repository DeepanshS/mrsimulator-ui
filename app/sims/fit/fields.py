# -*- coding: utf-8 -*-
import json
from datetime import datetime

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import callback_context as ctx
from dash import no_update
from dash.dependencies import ALL
from dash.dependencies import Input
from dash.dependencies import MATCH
from dash.dependencies import Output
from dash.dependencies import State
from dash.exceptions import PreventUpdate
from lmfit import Parameters
from mrsimulator import parse
from mrsimulator.utils.spectral_fitting import make_LMFIT_params

from app import app


CSS_STR = "*{font-family:'Helvetica',sans-serif;}td{padding: 0 8px}"
TITLE = {"sys": "Spin System", "mth": "Method", "SP": "Method"}
GROUPING = {"Spin System": ["sys"], "Method": ["mth", "SP"]}


def inputs():
    """Parameters input html div"""
    return html.Div(id="params-table-div", children=[])


def modals():
    """Hidden modals div"""
    return html.Div(id="params-modals-div", children=[], hidden=False)


def report():
    """LMFIT report html div"""
    return html.Div(id="params-report-div", children=[])


def ui():
    """Main UI for fitting interface"""
    return html.Div(
        children=[inputs(), modals(), report()],
        id="input-fields",
        className="fit-scroll",
    )


fields = ui()


# Callbacks ============================================================================
# Two callbacks are needed to avoid circular dependency error
@app.callback(
    Output("params-data", "data"),
    Output("trigger-sim", "data"),
    Output("trigger-fit", "data"),
    Input("simulate-button", "n_clicks"),
    Input("run-fitting-button", "n_clicks"),
    State("local-mrsim-data", "data"),
    State("params-data", "data"),
    State({"kind": "name", "name": ALL}, "children"),  # Requires states to be generated
    State({"kind": "value", "name": ALL}, "value"),  # to be made in the order which
    State({"kind": "vary", "name": ALL}, "checked"),  # they appear on the page.
    State({"kind": "min", "name": ALL}, "value"),
    State({"kind": "max", "name": ALL}, "value"),
    State({"kind": "expr", "name": ALL}, "value"),
    prevent_initial_call=True,
)
def update_fit_data(n1, n2, mr_data, p_data, *vals):
    """Main fitting callback dealing with data management"""
    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print("fit data", trigger_id)

    return CALLBACKS[trigger_id](vals)


@app.callback(
    Output("params-table-div", "children"),  # List of table
    Output("params-modals-div", "children"),  # List of modals
    Output("sys-select-div", "children"),  # dcc.buttonGroup
    Output("mth-select-div", "children"),  # dcc.buttonGroup
    Output("params-report-div", "children"),  # html string
    Output("params-report-div", "hidden"),  # bool
    Input({"kind": "delete", "name": ALL}, "n_clicks"),
    Input("refresh-button", "n_clicks"),
    Input("trigger-table-update", "data"),
    State("local-mrsim-data", "data"),
    State({"kind": "name", "name": ALL}, "children"),  # Requires states to be generated
    State({"kind": "value", "name": ALL}, "value"),  # to be made in the order which
    State({"kind": "vary", "name": ALL}, "checked"),  # they appear on the page.
    State({"kind": "min", "name": ALL}, "value"),
    State({"kind": "max", "name": ALL}, "value"),
    State({"kind": "expr", "name": ALL}, "value"),
    prevent_initial_call=True,
)
def update_fit_elements(n1, n2, trig, mr_data, *vals):
    "Main fitting callback dealing with visible elements"
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print("fit elements", trigger_id)

    if trigger_id.startswith("{"):
        py_dict = json.loads(trigger_id)
        name, trigger_id = py_dict["name"], py_dict["kind"]
        return CALLBACKS[trigger_id](name, vals)

    return CALLBACKS[trigger_id](vals)


# Opens/closes params modal
app.clientside_callback(
    "function (n1, is_open) { if(n1 == null) { return false; } return !is_open; }",
    Output({"kind": "modal", "parrent": MATCH}, "is_open"),
    Input({"kind": "modal-btn", "parrent": MATCH}, "n_clicks"),
    # Input({"kind": "modal-sub-btn", "parrent": MATCH}, "n_clicks"),
    State({"kind": "modal", "parrent": MATCH}, "is_open"),
    prevent_initial_call=True,
)


# # Sets visibility of selected spin system and method
# app.clientside_callback(
#     """function (n, className) {
#         let check = className.includes('active');
#         if (check) return className.replace('active', '').trim();
#         if (!check) return `${className} active`;
#     }""",
#     Output({"key": "fit-table", "index": MATCH}, "className"),
#     Input({"key": "fit-table-select-btn", "index": MATCH}, "value"),
#     State({"key": "fit-table", "index": MATCH}, "className"),
#     prevent_initial_call=True,
# )

# , "title": MATCH
# @app.callback(
#     Output({"key": "fit-table", "index": ALL}, "className"),
#     Input({"key": "fit-table-select-btn", "title": ALL}, "value"),
#     State({"key": "fit-table", "index": ALL}, "className"),
#     prevent_initial_call=True
# )
# def set_table_visibility(set_index, *args):
#     print("table vis")
#     arr = [no_update] * len(args)
#     if "fields-table active" not in args:
#         return arr

#     active_index = args.index("fields-table active")
#     arr[active_index] = "fields-table"
#     arr[set_index] = "fields-table active"


# Helper Methods =======================================================================
def update_params_and_simulate(vals):
    """Updates stored Parameters object JSON and triggers a simulation"""
    return get_new_params_json(vals), int(datetime.now().timestamp() * 1000), no_update


def update_params_and_fit(vals):
    """Updates stored Parameters object JSON and triggers fitting"""
    return get_new_params_json(vals), no_update, int(datetime.now().timestamp() * 1000)


def delete_param(name, vals):
    """Deletes specified param (row) from interface"""
    params_data = get_new_params_json(vals)
    params_obj = Parameters().loads(params_data)

    name = name.split("-")[1]
    # Add check to make sure name is in params
    del params_obj[name]


    params_dict = params_obj_to_dict(params_obj)
    sys_params, mth_params = group_params(params_dict)
    out = {
        "tables": [fit_table(*item) for item in (sys_params + mth_params)],
        "modals": [make_modals_div(params_dict)],
        "select": [no_update] * 2,
        "report": [no_update] * 2,
    }

    # tables = make_fit_tables(params_obj_to_dict(params_obj))
    # modals = make_modals_div(params_obj_to_dict(params_obj))

    # return tables, modals, no_update, no_update

    return expand_out(out)


def reset_params_body(*args):
    return update_tables(*args, reset=True)


def update_params_body(*args):
    return update_tables(*args)


def update_tables(*args, reset=False):
    data = ctx.states["local-mrsim-data.data"]

    if len(data["spin_systems"]) == 0:
        return expand_out(
            {
                "tables": [fit_table({}, 0)],
                "modals": [no_update],
                "select": [select_buttons([], "Spin Systems"), select_buttons([], "Methods")],
                "report": [no_update, True],  # Should report be hidden on fail?
            }
        )

    sim, processor, report = parse(data)

    if "params" in data and data["params"] is not None and not reset:
        params_obj = Parameters().loads(data["params"])
    else:
        params_obj = make_LMFIT_params(sim, processor, include={"rotor_frequency"})

    params_dict = params_obj_to_dict(params_obj)
    sys_params, mth_params = group_params(params_dict)
    print(len(sys_params + mth_params))

    tables = [fit_table(*item) for item in (sys_params + mth_params)[0]]
    modals = make_modals_div(params_dict)
    sys_sel = select_buttons(sys_params, "Spin Systems")
    mth_sel = select_buttons(mth_params, "Methods")


    out = {
        "tables": tables,
        "modals": modals,
        "select": [sys_sel, mth_sel],
        "report": ["", True]
        if "report" not in data
        else [data["report"], False],  # Hidden should be changed
    }

    return expand_out(out)
    # return tables, modals, sys_sel, mth_sel, no_update, no_update


def make_modals_div(params_dict):
    """Constructs hidden html.Div containing params modals

    Params:
        params_dict: dict representation of Parameters object

    Returns:
        list of modals
    """

    def make_modal(key, vals):
        """Helper method to make each modal"""
        min_id = {"name": f"{key}-min", "kind": "min"}
        max_id = {"name": f"{key}-max", "kind": "max"}
        expr_id = {"name": f"{key}-expr", "kind": "expr"}
        modal_id = {"kind": "modal", "parrent": key}

        min_ = html.Div(
            ["Minimum", dcc.Input(value=vals["min"], id=min_id)], className="input-form"
        )
        max_ = html.Div(
            ["Maximum", dcc.Input(value=vals["max"], id=max_id)], className="input-form"
        )
        expr = html.Div(
            ["Expression", dcc.Input(value=vals["expr"], type="text", id=expr_id)],
            className="input-form",
        )

        head = dbc.ModalHeader(html.B(key))
        body = dbc.ModalBody([min_, max_, expr])
        # foot = dbc.ModalFooter("Values automatically update on modal? close")

        return dbc.Modal([head, body], id=modal_id)

    modals = []
    for key, vals in params_dict.items():
        modals += [make_modal(key, vals)]

    return modals


def group_params(params_dict):
    """Groups params_dict based on `GROUPING`

    Params:
        params_dict: dict reporesentation of whole Parameters object

    Returns:
        sys_group: list of spin system (dict, int, str) tuples
        mth_group: list of method (dict, int, str) tuples
    """
    sys_group, mth_group = [], []
    keys = list(params_dict.keys())

    if len(keys) == 0:
        return {}

    tmp_sys, tmp_mth = [], []
    index_sys, index_mth, index_tot = 0, 0, 0
    for key in keys:
        group, index = key.split("_")[0], int(key.split("_")[1])
        if group in GROUPING["Spin System"]:
            if index_sys != index:
                sys_group.append(
                    (
                        {k: params_dict[k] for k in tmp_sys},
                        index_tot,
                        f"Spin System {index_sys}",
                    )
                )
                index_sys += 1
                index_tot += 1
                tmp_sys = []
            tmp_sys += [key]
        elif group in GROUPING["Method"]:
            if index_mth != index:
                mth_group.append(
                    (
                        {k: params_dict[k] for k in tmp_mth},
                        index_tot,
                        f"Method {index_mth}",
                    )
                )
                index_mth += 1
                index_tot += 1
                tmp_mth = []
            tmp_mth += [key]

    sys_group.append(
        ({k: params_dict[k] for k in tmp_sys}, index_tot, f"Spin System {index_sys}")
    )
    mth_group.append(
        ({k: params_dict[k] for k in tmp_mth}, index_tot + 1, f"Method {index_mth}")
    )

    return sys_group, mth_group


def select_buttons(params_list, title):
    """Makes selectons buttons for spin systems/methods"""
    select = []  # `title` is 'Spin Systems' or 'Methods'
    # for i, item in enumerate(params_list):
    #     select.append(html.Button(i, id={"key": "fit-table-btn", "index": item[1]}))

    btn_group = dcc.RadioItems(
        id={"key": "fit-table-select-btn", "title": title},
        # className="btn-group",
        # labelClassName="",
        # labelCheckedClassName="",
        labelStyle={"display", "inline-block"},
        options=[
            {"label": i, "value": item[1]} for i, item in enumerate(params_list)
        ],
        value=params_list[0][1]
    )

    select.append(btn_group)

    return btn_group


# Truncate decimal places (using css?)
def fit_table(_dict, index, title="Name"):
    """Constructs html table of parameter inputs fields

    Params:
        _dict: slice from dict representation of Parameters object
        index: index of table used for callback visibility
        title: string to display in second column header

    Returns:
        html.Table
    """
    fit_header = ["", title, "Value", "", ""]
    fit_rows = [html.Thead(html.Tr([html.Th(html.B(item)) for item in fit_header]))]

    input_args = {"type": "number", "autoComplete": "off"}
    for key, vals in _dict.items():
        vary_id = {"name": f"{key}-vary", "kind": "vary"}
        name_id = {"name": f"{key}-label", "kind": "name"}
        val_id = {"name": f"{key}-value", "kind": "value"}
        mod_btn_id = {"kind": "modal-btn", "parrent": key}
        del_id = {"name": f"delete-{key}-row", "kind": "delete"}

        name = html.Div(id=name_id, children=key)
        vary = dbc.Checkbox(id=vary_id, checked=vals["vary"])
        val = dcc.Input(id=val_id, value=vals["value"], **input_args)

        modal_ic = html.Span(
            html.I(className="fas fa-sliders-h", title="More Settings"),
            id=mod_btn_id,
            className="icon-button",
        )

        del_ic = html.Span(
            html.I(className="fas fa-times", title="Remove Parameter"),
            id=del_id,
            className="icon-button",
        )

        pack = [vary, name, val, modal_ic, del_ic]
        fit_rows += [html.Thead(html.Tr([html.Td(item) for item in pack]))]

    return html.Table(
        className="fields-table active" if title[-1] == "0" else "fields-table",  # Visibility callback currently flips `active` on table creation
        children=fit_rows,
        id={"key": "fit-table", "index": index},
    )


def params_obj_to_dict(params_obj):
    """Makes dictionary representation of params object from json string
    Params:
        params_obj: Parameters object

    Return:
        params_dict: dictionary of lmfit parameters
    """
    KEY_LIST = ["vary", "value", "min", "max", "expr"]

    return {
        name: {key: getattr(param, key) for key in KEY_LIST}
        for name, param in params_obj.items()
    }


def get_new_params_json(vals):
    """Returns new Parameters JSON dump from input values"""
    zip_vals = list(zip(*vals))
    new_obj = Parameters()

    for row in zip_vals:
        new_obj.add(*row)

    return new_obj.dumps()


CALLBACKS = {
    "simulate-button": update_params_and_simulate,
    "run-fitting-button": update_params_and_fit,
    "refresh-button": reset_params_body,
    "trigger-table-update": update_params_body,
    "delete": delete_param,
}


def expand_out(out):
    """Helper method for return values of `update_fit_elements`"""
    print([
        out["tables"],
        out["modals"],
        *out["select"],
        *out["report"],
    ])
    return [
        out["tables"],
        out["modals"],
        *out["select"],
        *out["report"],
    ]


# def make_fit_tables(params_dict):
#     """Makes list of grouped html.Table elements

#     Params:
#         params_dict: dict reporesentation of whole Parameters object

#     Returns:
#         tables: list of html.Table
#     """
#     tables = []
#     # Slice params_dict
#     keys = list(params_dict.keys())

#     if len(keys) == 0:
#         return

#     prefix = keys[0][:5]
#     tmp = []
#     search_sys = ["Spin Systems"]
#     search_mth = ["Methods"]

#     # Needs cleaned up
#     index_sys, index_mth, index = 0, 0, 0
#     for key in keys:
#         if key[:5] != prefix:
#             if tmp[0][:3] == "sys":
#                 search_sys.append(
#                     html.Button(index_sys, id={"key": "fit-table-btn", "index": index})
#                 )
#                 index_sys += 1
#             else:
#                 search_mth.append(
#                     html.Button(index_mth, id={"key": "fit-table-btn", "index": index})
#                 )
#                 index_mth += 1
#             lst = tmp[0].split("_")
#             title = f"{TITLE[lst[0]]} {lst[1]}"
#             tables.append(fit_table({k: params_dict[k] for k in tmp}, index, title))
#             tmp, prefix = [], key[:5]
#             index += 1

#         tmp.append(key)

#     if tmp[0][:3] == "sys":
#         search_sys.append(
#             html.Button(index_sys, id={"key": "fit-table-btn", "index": index})
#         )
#     else:
#         search_mth.append(
#             html.Button(index_mth, id={"key": "fit-table-btn", "index": index})
#         )
#     lst = tmp[0].split("_")
#     title = f"{TITLE[lst[0]]} {lst[1]}"
#     tables.append(
#         fit_table(
#             {k: params_dict[k] for k in tmp},
#             index,
#             title,
#         )
#     )

#     return html.Div([html.Div(search_sys), html.Div(search_mth), html.Div(tables)])