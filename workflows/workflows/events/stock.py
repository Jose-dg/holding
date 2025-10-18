from __future__ import annotations

import frappe
from frappe.utils import today

def check_replenishment_on_stock_update(doc, method=None):
    """
    Called on submit of Sales Invoice or POS Invoice.
    Checks if any item's stock has fallen below reorder level
    and creates a Material Request if needed.
    """
    target_company = "Diem"
    if doc.company != target_company:
        return

    # Agrupa los items por almacén para optimizar las consultas
    items_by_warehouse = {}
    for item in doc.items:
        if not item.warehouse:
            continue
        if item.warehouse not in items_by_warehouse:
            items_by_warehouse[item.warehouse] = []
        items_by_warehouse[item.warehouse].append(item.item_code)

    for warehouse, items in items_by_warehouse.items():
        create_request_for_warehouse_if_needed(warehouse, items)


def create_request_for_warehouse_if_needed(warehouse: str, item_codes: list[str]):
    supplying_company = "Money for gamers"
    items_to_request = []

    for item_code in item_codes:
        reorder_rule = frappe.db.get_value(
            "Item Reorder",
            {"parent": item_code, "warehouse": warehouse},
            ["reorder_level", "reorder_qty"],
            as_dict=True,
        )

        if not reorder_rule:
            continue

        current_stock = frappe.db.get_value(
            "Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"
        )

        if current_stock is None or current_stock >= reorder_rule.reorder_level:
            continue

        # Prevenir duplicados: verificar si ya existe una solicitud de material abierta
        already_requested = frappe.db.exists(
            "Material Request Item",
            {
                "item_code": item_code,
                "warehouse": warehouse,
                "docstatus": 0,  # 0 = Borrador (Draft)
            },
        )
        if already_requested:
            continue

        items_to_request.append(
            {
                "item_code": item_code,
                "qty": reorder_rule.reorder_qty or 1,
                "warehouse": warehouse,
                "schedule_date": today(),
            }
        )

    if not items_to_request:
        return

    # Crear una única Solicitud de Material para todos los artículos necesarios en este almacén
    material_request = frappe.get_doc(
        {
            "doctype": "Material Request",
            "material_request_type": "Purchase",
            "company": frappe.db.get_value("Warehouse", warehouse, "company"),
            "schedule_date": today(),
            "items": items_to_request,
        }
    )
    material_request.set_supplier(supplying_company)
    material_request.insert(ignore_permissions=True)
    material_request.submit()
    frappe.db.commit()

    frappe.log_error(
        title="Real-time Replenishment Request",
        message=f"Created Material Request {material_request.name} for warehouse {warehouse}",
    )
