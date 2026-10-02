"""ERP tools: budget lookups, generic ERP reads, and purchase-order creation."""
from __future__ import annotations

from typing import Any

from app.identity import RunIdentity
from app.tools import Tool

ERP_READ_SCOPE = "erp.read"
ERP_PO_WRITE_SCOPE = "erp.read erp.po.create"


def tools(deps) -> list[Tool]:
    erp = deps.erp

    async def get_budget(args: dict[str, Any], ident: RunIdentity) -> Any:
        return await erp.call(
            "budget.get_remaining",
            {"business_unit": ident.tenant, "department": args["department"], "fiscal_period": args["fiscal_period"]},
            ident,
            ERP_READ_SCOPE,
        )

    async def erp_call(args: dict[str, Any], ident: RunIdentity) -> Any:
        arguments = dict(args.get("arguments", {}))
        arguments["business_unit"] = ident.tenant
        return await erp.call(args["operation"], arguments, ident, deps.erp_scope_for(args["operation"]))

    async def create_purchase_order(args: dict[str, Any], ident: RunIdentity) -> Any:
        return await erp.call(
            "po.create",
            {
                "business_unit": ident.tenant,
                "department": args["department"],
                "vendor_id": args["vendor_id"],
                "lines": args["lines"],
                "currency": args["currency"],
                "source_doc_id": args["source_doc_id"],
                "client_reference": args["source_doc_id"],
            },
            ident,
            ERP_PO_WRITE_SCOPE,
        )

    line_schema = {
        "type": "object",
        "properties": {
            "sku": {"type": "string", "maxLength": 64},
            "description": {"type": "string", "maxLength": 256},
            "quantity": {"type": "number", "exclusiveMinimum": 0},
            "unit_price_cents": {"type": "integer", "minimum": 0},
        },
        "required": ["sku", "quantity", "unit_price_cents"],
        "additionalProperties": False,
    }

    return [
        Tool(
            name="get_budget",
            description="Remaining budget for a department in a fiscal period.",
            input_schema={
                "type": "object",
                "properties": {
                    "department": {"type": "string", "maxLength": 64},
                    "fiscal_period": {"type": "string", "pattern": "^FY[0-9]{4}-Q[1-4]$"},
                },
                "required": ["department", "fiscal_period"],
                "additionalProperties": False,
            },
            invoke=get_budget,
        ),
        Tool(
            name="erp_call",
            description=(
                "Look up ERP records (vendors, invoices, purchase orders, budgets). "
                "operation is an ERP operation name such as vendor.get or invoice.list_open."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "maxLength": 64},
                    "arguments": {"type": "object"},
                },
                "required": ["operation"],
                "additionalProperties": False,
            },
            invoke=erp_call,
        ),
        Tool(
            name="create_purchase_order",
            description="Raise a purchase order in the ERP for an approved quote.",
            input_schema={
                "type": "object",
                "properties": {
                    "department": {"type": "string", "maxLength": 64},
                    "vendor_id": {"type": "string", "maxLength": 32},
                    "currency": {"type": "string", "pattern": "^[A-Z]{3}$"},
                    "source_doc_id": {"type": "string", "maxLength": 64},
                    "lines": {"type": "array", "items": line_schema, "maxItems": 200},
                },
                "required": ["department", "vendor_id", "currency", "source_doc_id", "lines"],
                "additionalProperties": False,
            },
            invoke=create_purchase_order,
            target_field="source_doc_id",
        ),
    ]
