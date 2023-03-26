# -*- coding: utf-8 -*-
from datetime import datetime

import dash_bootstrap_components as dbc
import numpy as np
from dash import dcc
from dash import html
from dash.dependencies import ClientsideFunction
from dash.dependencies import Input
from dash.dependencies import Output
from dash.dependencies import State
from dash.exceptions import PreventUpdate

from app import app
from app.custom_widgets import custom_button
from app.sims import post_simulation as ps
from app.sims.method import fields as mrf
from app.sims.method.modal import method_selection_modal
from app.sims.method.modal import SUPPORTED_METHODS

__author__ = ["Deepansh J. Srivastava"]
__email__ = "srivastava.89@osu.edu"
N_DIMS = 2


def hidden_method_select_element():
    """Hiddent element to hold method index for Python side and update plot."""
    return dcc.Input(id="select-method", value=0, type="number", className="hidden")


def post_simulation_ui():
    """post simulation signal processing user interface"""
    proc_tools = html.Div(ps.tools())
    page_content = [ps.scale.page, ps.convolution.page]
    page = html.Div(page_content, id="post_sim_child", className="method-scroll")
    return html.Div([proc_tools, page])


def dimensions_ui():
    """dimensions user interface"""
    return [mrf.spectral_dimension_ui(i) for i in range(N_DIMS)]


def method_property_tab_ui():
    """method property interface as tab"""
    contents = [mrf.experiment_ui(), mrf.global_environment(), *dimensions_ui()]
    return dbc.Tab(
        label="Properties", children=contents, class_name="tab-scroll method"
    )


def signal_processing_tab_ui():
    """signal processing interface as tab"""
    return dbc.Tab(
        label="Signal Processing",
        children=post_simulation_ui(),
        class_name="tab-scroll method",
    )


app.clientside_callback(
    """function(val) {
        if (val === 'tab-0') { return [{'display': 'none'}, {'display': 'block'}]; }
        if (val === 'tab-1') { return [{'display': 'block'}, {'display': 'none'}]; }
    }""",
    Output("signal-processor-div", "style"),
    Output("apply-method-div", "style"),
    Input("method-tabs", "active_tab"),
    prevent_initial_call=True,
)


def default_display():
    """Default display when no method object is present"""
    comment = html.H5("Load methods or start creating")
    icon = html.I(className="fas fa-cube fa-4x")
    sub_text = html.H6("Add a method")
    title = html.Span([icon, sub_text], id="open-edit_method")
    return html.Div([comment, title], className="blank-display")


def scrollable():
    """Scrollable left panel for method info"""
    default = default_display()
    app.clientside_callback(
        """function(n) {
            document.getElementById("add-method-button").click();
            throw window.dash_clientside.PreventUpdate;
        }""",
        Output("open-edit_method", "children"),
        Input("open-edit_method", "n_clicks"),
        prevent_initial_call=True,
    )
    method_read_only = html.Div(default, id="method-read-only")
    return html.Div(method_read_only, className="slider1")


def tools():
    """Add, duplicate, or remove methods"""
    new = html.Button(id="add-method-button")
    duplicate = html.Button(id="duplicate-method-button")
    remove = html.Button(id="remove-method-button")

    return html.Div(children=[new, duplicate, remove], style={"display": "none"})


def header():
    """Method section header"""
    icon = html.I(className="fas fa-cube fa-lg")
    text = html.H4("Methods", className="hide-label-sm")
    title = html.Div([icon, text])
    search = dcc.Input(
        value="", id="search-method", placeholder="Search methods", type="search"
    )
    return html.Div([title, search], className="card-header")


def layout():
    """Method layout"""
    label = html.Label(id="method-title")
    title = html.Div(label, className="ui_title")

    # submit method button
    submit = custom_button(
        text="Submit Method", id="apply-method-changes", tooltip="Submit Method"
    )
    submit = html.Div(
        submit,
        id="apply-method-div",
        style={"display": "block"},
        className="submit-button",
    )

    # submit processing button
    submit_pro = custom_button(
        text="Submit Processor",
        id="submit-signal-processor-button",
        tooltip="Submit Processor",
    )
    submit_pro = html.Div(
        submit_pro,
        id="signal-processor-div",
        style={"display": "none"},
        className="submit-button",
    )

    # tabs
    tabs = dbc.Tabs(
        [method_property_tab_ui(), signal_processing_tab_ui()], id="method-tabs"
    )

    # method layout
    return html.Div(
        [html.Div([title, tabs]), submit, submit_pro],
        id="method-editor-content",
        className="slider2",
    )


def user_interface():
    """method user interface"""
    head = header()
    body = html.Div(
        [scrollable(), layout(), tools(), hidden_method_select_element()],
        id="met-slide",
        className="slide-offset",
    )

    return html.Div(
        className="left-card",
        children=html.Div([head, body, method_selection_modal]),
        id="methods-body",
    )


def generate_sidepanel(method, index):
    """Generate scrollable side panel listing for methods"""
    title = html.B(f"Method {index}", className="")

    # method name
    name = html.Div(method["name"], className="")

    # method channel(s)
    channels = ", ".join(method["channels"])
    channels = html.Div(f"Channel: {channels}")

    # n dimensions
    n_dim = len(method["spectral_dimensions"])
    n_dim = html.Div(f"Dimensions: {n_dim}")

    a_tag = html.A([title, name, channels, n_dim])

    # The H6(index) only shows for smaller screen sizes.
    return html.Li(
        [html.H6(index), html.Div(a_tag)],
        # draggable="true",
        className="list-group-item",
        # id={"type": "select-method-index", "index": index},
    )


def refresh(methods):
    """Return a html for rendering the display in the read-only spin-system section."""
    output = [generate_sidepanel(mth, i) for i, mth in enumerate(methods)]
    if output == []:
        return default_display()
    return html.Div(
        [html.Ul(output, className="list-group")], className="scrollable-list"
    )


method_body = user_interface()


# callback code section =======================================================
@app.callback(
    Output("add-method-from-template", "data"),
    Input("close-method-selection", "n_clicks"),
    State("method-type", "value"),
    State("channel", "value"),
    prevent_initial_call=True,
)
def get_method_json(n_clicks, value, isotope):
    """callback for default method template"""
    if n_clicks is None:
        raise PreventUpdate

    selected_method = SUPPORTED_METHODS[value]

    return {
        "method": selected_method["function"](
            channels=[isotope],
            spectral_dimensions=selected_method["spectral_dimensions"],
        ).json(),
        "time": int(datetime.now().timestamp() * 1000),
    }


def sigma_helper(x0, dx, shape_x0, shape_x1, y_values):
    """Calculates standard deviation from given graph parameters

    Params:
        x0: leftmost x value of scatter plot
        dx: step between points on plot
        shape_x0: x0 (first) point on shape
        shape_x1: x1 (second) point on shape
        y_values: ordered list of y values on scatter plot
    """
    if dx > 0:
        print("positive dx")
        # swap the limits if dx is positive, and negate dx
        shape_x1, shape_x0 = shape_x0, shape_x1
        dx *= -1

    # Choose leftmost box bound OR leftmost point if box is out of left bound
    x_left = min(max(shape_x1, shape_x0), x0)
    # Choose rightmost box bound OR rightmost point if box is out of right bound
    x_right = max(min(shape_x1, shape_x0), x0 + (len(y_values) * dx))
    x_range = x_right - x_left
    start_index = max(0, round((x_left - x0) / dx))
    end_index = min(len(y_values), round(x_range / dx) + start_index)
    selected_values = y_values[start_index:end_index]

    if selected_values == []:
        print("no points in bounds")
        # Display error message "no points selected"
        raise PreventUpdate

    return np.std(selected_values)


@app.callback(
    Output("measurement-sigma", "value"),
    Input("calc-sigma-button", "n_clicks"),
    State("nmr_spectrum", "figure"),  # Graph selection and values
    prevent_initial_call=True,
)
def calculate_sigma(n1, fig):
    """Calculates standard deviation of noise on selected part of graph"""
    print("sigma btn")
    # print(fig)

    if "shapes" not in fig["layout"]:
        print("no shapes in layout")
        # Display error message "no area selected?"
        raise PreventUpdate

    if len(fig["layout"]["shapes"]) > 1:
        print("shapes array too long")
        # Display error message "too many selections?"
        raise PreventUpdate

    shape = fig["layout"]["shapes"][0]
    if shape["type"] != "rect" and shape["type"] != "circle":
        print("wrong type of shape")
        # Display error message "please draw a rect or circle?"
        raise PreventUpdate

    exp = next((item for item in fig["data"] if item["name"] == "experiment"), None)
    if exp is None:
        print("experiment not found in figure")
        # Display error message "experiment not found in figure?"
        raise PreventUpdate

    return sigma_helper(
        x0=exp["x0"],
        dx=exp["dx"],
        shape_x0=shape["x0"],
        shape_x1=shape["x1"],
        y_values=exp["y"],
    )


app.clientside_callback(
    """function (n1, value) {
        let index = window.method.getIndex();
        if (index == value) throw window.dash_clientside.PreventUpdate;
        return index;
    }
    """,
    Output("select-method", "value"),
    Input("force-refresh-method", "n_clicks"),
    State("select-method", "value"),
    prevent_initial_call=True,
)

app.clientside_callback(
    ClientsideFunction(namespace="method", function_name="updateMethodJson"),
    Output("new-method", "data"),
    Input("apply-method-changes", "n_clicks"),
    Input("add-method-from-template", "modified_timestamp"),
    Input("duplicate-method-button", "n_clicks"),
    Input("remove-method-button", "n_clicks"),
    State("add-method-from-template", "data"),
    prevent_initial_call=True,
)
