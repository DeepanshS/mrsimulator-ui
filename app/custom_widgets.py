# -*- coding: utf-8 -*-
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input
from dash.dependencies import Output
from dash.dependencies import State

from . import app

__author__ = "Deepansh J. Srivastava"
__email__ = "srivastava.89@osu.edu"


tooltip_format = {"placement": "bottom", "delay": {"show": 250, "hide": 10}}


def label_with_help_button(label="", help_text="", id=None):
    """A custom label with a help icon.

    Args:
        label: A string label
        help_text: A string message displayed as help message.
        id: The id for the label.
    """
    label = dbc.Label(label, className="formtext pr-1")
    help_ = custom_hover_help(message=help_text, id=f"upload-{id}-url-help")
    className = "d-flex justify-content-start align-items-center"
    return html.Div([label, help_], className=className)


def custom_hover_help(message="", id=None):
    """A custom help button.

    Args:
        message: A string message displayed as help message.
        id: The id for the label.
    """
    style = {"color": "white", "cursor": "pointer"}
    icon = html.I(className="fas fa-question-circle", style=style, title=message)
    return html.Div(icon, id=id, className="align-self-start")


def custom_button(
    text="",
    children="",
    icon_classname="",
    id=None,
    tooltip=None,
    module="dbc",
    **kwargs,
):
    """A custom dash bootstrap component button with added tooltip and icon option.

    Args:
        text: A string text displayed on the button.
        icon_classname: A string given as the className, for example, "fas fa-download".
                See https://fontawesome.com for strings.
        id: A string with button id.
        tooltip: A string with tooltip, diplayed when cursor hovers over the button.
        kwargs: additional keyward arguments for dash-bootstrap-component button.
    """

    label = html.Span([text, children], className="hide-label-sm pl-1")
    if icon_classname != "":
        icon = html.I(className=icon_classname, title=tooltip)
        label = html.Span([icon, label], className="d-flex align-items-center")

    obj = dbc.Button if module == "dbc" else html.Button
    return obj(label, id=id, **kwargs)


def custom_switch(text="", icon_classname="", id=None, tooltip=None, **kwargs):
    """A custom dash bootstrap component boolean button with added tooltip and icon option.

    Args:
        text: A string text displayed on the button.
        icon_classname: A string given as the className, for example, "fas fa-download".
                See https://fontawesome.com for strings.
        id: A string with button id.
        tooltip: A string with tooltip, diplayed when cursor hovers over the button.
        kwargs: additional keyward arguments for dash-bootstrap-component button.
    """
    button = custom_button(
        text=text, icon_classname=icon_classname, id=id, tooltip=tooltip, **kwargs
    )

    app.clientside_callback(
        "function (n, active) { return !active; }",
        Output(id, "active"),
        Input(id, "n_clicks"),
        State(id, "active"),
        prevent_initial_call=True,
    )

    return button


def custom_card(text, children, id_=None):
    if id_ is None:
        return html.Div([html.H6(text), children], className="scroll-cards")
    return html.Div([html.H6(text), children], id=id_, className="scroll-cards")


def custom_slider(label="", return_function=None, **kwargs):
    """
    A custom dash bootstrap component slider with added components-
    slider-label, slider-bar, and a slider-text reflecting the current value
    of the slider.

    Args:
        label: A string with the label.
        return_function: This function will be applied to the current
            value of the slider before updating the slider-text.
        kwargs: additional keyward arguments for dash-bootstrap-component Input.
    """
    id_label = kwargs["id"] + "_label"
    slider = html.Div(
        [
            html.Div(
                [label, dbc.FormText(id=id_label)],
                className="d-flex justify-content-between",
            ),
            dcc.Slider(**kwargs, className="slider-custom"),
        ]
    )

    @app.callback(
        [Output(id_label, "children")],
        [Input(kwargs["id"], "value")],
        prevent_initial_call=True,
    )
    def update_label(value):
        if return_function is None:
            return [value]
        return [return_function(value)]

    return slider


def custom_input_group(
    prepend_label="", append_label=None, input_type="number", **kwargs
):
    """
    A custom dash bootstrap component input-group widget with a prepend-label,
    followed by an Input box, and an append-label.

    Args:
        prepend_label: A string to prepend dash-bootstrap-component Input widget.
        append_label: A string to append dash-bootstrap-component Input widget.
        kwargs: additional keyward arguments for dash-bootstrap-component Input.
    """
    append_label = append_label if append_label is not None else ""

    append_ui = html.Label(className="label-right", children=append_label)
    prepend_ui = html.Label(className="label-left", children=prepend_label)
    input_ui = dcc.Input(type=input_type, autoComplete="off", **kwargs)

    return html.Div([prepend_ui, input_ui, append_ui], className="input-form")


def custom_collapsible(
    text="", tooltip=None, identity=None, children=None, is_open=True, size="md"
):
    """
    A custom collapsible widget with a title and a carret dropdown icon.

    Args:
        text: A string with the title of the collapsible widget.
        identity: An id for the widget.
        children: A dash-bootstrap componets or a list of components.
        is_open: Boolean. If false, the widget is collapsed on initial render.
        size: String, "sm, md, lg".
        button_classname: String. css classnames for button toggler.
        collapse_classname: String. css classnames for collapsible.
    """
    collapse_classname = "panel-collapse collapse in content"
    if is_open:
        collapse_classname += " show"

    class_name = "d-flex justify-content-between align-items-center"
    chevron_icon = html.I(className="icon-action fas fa-chevron-down", title=tooltip)
    btn_text = html.Div([text, chevron_icon], className=class_name)

    layout = [
        html.Button(
            btn_text,
            style={"color": "black"},
            **{
                "data-toggle": "collapse",
                "data-target": f"#{identity}-collapse",
                "aria-expanded": "true",
            },
            className=f"collapsible btn btn-link btn-block btn-{size}",
        ),
        html.Div(
            id=f"{identity}-collapse", children=children, className=collapse_classname
        ),
    ]

    return html.Div(layout)


def container(text, featured, **kwargs):
    children = html.Div(featured, className="container")
    return custom_card(text=html.Div(text), children=children, **kwargs)


def collapsable_card(text, id_, featured, hidden=None, message=None):
    # collapsable button
    icon = html.I(className="fas fa-chevron-down", title=message)
    vis = {"visibility": "hidden"} if hidden is None else {"visibility": "visible"}
    chevron_down_btn = html.Label(
        icon,
        id=f"{id_}-collapse-button",
        style=vis,
        **{
            "data-toggle": "collapse",
            "data-target": f"#{id_}-collapse-fields",
            "aria-expanded": "true",
        },
    )

    # featured fields
    featured = [html.Div(featured)]
    text = [text] if not isinstance(text, list) else text
    text.append(chevron_down_btn)

    # collapsed fields
    if hidden is not None:
        featured += [dbc.Collapse(hidden, id=f"{id_}-collapse-fields", is_open=False)]

    content = custom_card(
        text=html.Div(text),
        children=html.Div(featured, className="container"),
    )
    return dbc.Collapse(content, id=f"{id_}-feature-collapse", is_open=True)
