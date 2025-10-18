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
        "on_submit": "workflows.workflows.events.stock.check_replenishment_on_stock_update",
    },
    "POS Invoice": {
        "on_submit": "workflows.workflows.events.stock.check_replenishment_on_stock_update",
    },
    "Sales Order": {
        "on_submit": "workflows.workflows.events.procurement.create_material_request_for_so",
    },
}

# Endpoint público para Shopify (ruta REST)
website_route_rules = [
    {
        "from_route": "/api/workflows/shopify/order",
        "to_route": "workflows.workflows.api.shopify.handle_shopify_order",
    }
]
