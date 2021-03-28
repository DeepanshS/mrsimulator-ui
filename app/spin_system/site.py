# -*- coding: utf-8 -*-
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input
from dash.dependencies import Output
from mrsimulator.spin_system.isotope import ISOTOPE_DATA

from app import app
from app.custom_widgets import collapsable_card
from app.custom_widgets import custom_input_group

isotope_options_list = [{"label": key, "value": key} for key in ISOTOPE_DATA.keys()]


def create_isotope_and_shift_fields():
    def isotope():
        """Isotope"""
        label = dbc.InputGroupAddon("Isotope", addon_type="prepend")
        select = dbc.Select(options=isotope_options_list, value="1H", id="isotope")

        # callback to hide the quadupolar fields when isotope is I=1/2
        app.clientside_callback(
            """
            function (isotope) {
                hideQuad();
                throw window.dash_clientside.PreventUpdate;
            }
            """,
            Output("isotope", "value"),
            [Input("isotope", "value")],
        )

        return dbc.InputGroup([label, select], className="input-form")

    # isotropic chemical shift
    isotropic_chemcial_shift_field = custom_input_group(
        prepend_label="Isotropic shift (δ)",
        append_label="ppm",
        id="isotropic_chemical_shift",
        debounce=True,
    )

    return html.Div(
        [isotope(), isotropic_chemcial_shift_field],
        className="container scroll-cards",
    )


def create_shielding_symmetric_fields():
    zeta_ui = custom_input_group(
        prepend_label="Anisotropy (ζ)",
        append_label="ppm",
        id="shielding_symmetric-zeta",
        debounce=True,
    )

    # asymmetry and Euler angles
    return create_collapsable_card_ui(zeta_ui, "shielding_symmetric")


def create_quadrupolar_fields():
    Cq_ui = custom_input_group(
        prepend_label="Coupling constant (Cq)",
        append_label="MHz",
        id="quadrupolar-Cq",
        debounce=True,
    )

    # asymmetry and Euler angles
    return create_collapsable_card_ui(Cq_ui, "quadrupolar")


def create_collapsable_card_ui(item, prefix):
    eta_ui = custom_input_group(
        prepend_label="Asymmetry (η)",
        append_label="",
        id=f"{prefix}-eta",
        debounce=True,
        min=0.0,
        max=1.0,
    )

    labels = ["alpha (α)", "beta (β)", "gamma (γ)"]
    keys = ["alpha", "beta", "gamma"]
    euler_angles_ui = [
        custom_input_group(
            prepend_label=label_,
            append_label="deg",
            id=f"{prefix}-{key_}",
            debounce=True,
        )
        for label_, key_ in zip(labels, keys)
    ]

    return collapsable_card(
        text=f"{prefix.replace('_',' ')}",
        id_=prefix,
        featured_fields=[item, eta_ui],
        hidden_fields=euler_angles_ui,
    )


def editor():
    isotope_and_shift = create_isotope_and_shift_fields()
    shielding_symmetric = create_shielding_symmetric_fields()
    quadrupolar = create_quadrupolar_fields()
    return html.Div([isotope_and_shift, shielding_symmetric, quadrupolar])
