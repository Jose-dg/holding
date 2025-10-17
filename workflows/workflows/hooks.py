from __future__ import annotations

app_name = "workflows"
app_title = "Workflows"
app_publisher = "You"
app_description = "Automatización de pines digitales e integraciones"
app_email = "you@example.com"
app_license = "MIT"

# Carga fixtures (Alegra Settings y Shopify Settings)
fixtures = ["alegra_shopify_settings.json"]

# Eventos de DocType
doc_events = {
    "Sales Invoice": {
        "on_submit": "workflows.workflows.events.intercompany.on_submit_sales_invoice",
    },
    "Serial No": {
        "on_update_after_submit": "workflows.workflows.events.fulfillment.try_pending",
    },
    "Stock Entry": {
        "on_update_after_submit": "workflows.workflows.events.fulfillment.try_pending",
    },
}

# Endpoint público para Shopify (ruta REST)
website_route_rules = [
    {"from_route": "/api/workflows/shopify/order", "to_route": "workflows.api.shopify.handle_shopify_order"}
]
