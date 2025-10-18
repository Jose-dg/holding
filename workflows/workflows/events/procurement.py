from __future__ import annotations

import frappe
from frappe.utils import today

def create_material_request_for_so(doc, method=None):
    """
    Called on submit of Sales Order.
    If the company is a 'back-to-back' company, check stock availability.
    If stock is insufficient, create a Material Request to procure the items.
    """
    back_to_back_companies = ["Laboratorio Clinica del Play", "Clinica del Play"]
    supplying_company = "Money for gamers"

    if doc.company not in back_to_back_companies:
        return

    items_to_procure = []

    for item in doc.items:
        projected_qty = frappe.db.get_value(
            "Bin",
            {"item_code": item.item_code, "warehouse": item.warehouse},
            "projected_qty",
        ) or 0

        if projected_qty < item.qty:
            qty_to_procure = item.qty - projected_qty
            
            # Prevenir duplicados: verificar si ya existe una solicitud de material abierta
            # para esta misma orden de venta.
            already_requested = frappe.db.exists(
                "Material Request Item",
                {
                    "item_code": item.item_code,
                    "warehouse": item.warehouse,
                    "sales_order": doc.name,
                    "docstatus": 0,
                },
            )
            if already_requested:
                continue

            items_to_procure.append(
                {
                    "item_code": item.item_code,
                    "qty": qty_to_procure,
                    "warehouse": item.warehouse,
                    "sales_order": doc.name,  # Enlazar a la Orden de Venta
                    "schedule_date": today(),
                }
            )

    if not items_to_procure:
        return

    material_request = frappe.get_doc(
        {
            "doctype": "Material Request",
            "material_request_type": "Purchase",
            "company": doc.company,
            "schedule_date": today(),
            "items": items_to_procure,
        }
    )
    material_request.set_supplier(supplying_company)
    material_request.insert(ignore_permissions=True)
    material_request.submit()
    frappe.db.commit()

    frappe.log_error(
        title="Back-to-Back Procurement Request",
        message=f"Created Material Request {material_request.name} for Sales Order {doc.name}",
    )
