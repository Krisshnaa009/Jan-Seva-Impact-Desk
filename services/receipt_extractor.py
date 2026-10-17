"""
Receipt extraction service.
Supports two modes:
  - mock   : Returns realistic fictional data without calling any external API.
  - ai     : Calls Google Gemini Vision to extract text from uploaded images.

The mock mode is always available and is the default when no API key is set.
"""
from __future__ import annotations

import base64
import json
import logging
import random
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Optional

from models.expense import ExpenseCategory, ExpenseRecord

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Mock dataset — realistic fictional receipts
# --------------------------------------------------------------------------- #

_MOCK_RECEIPTS = [
    {
        "vendor": "Annapoorna Grocery Store",
        "amount": "4850.00",
        "currency": "INR",
        "description": "Monthly ration supplies for community kitchen",
        "category": ExpenseCategory.FOOD,
        "receipt_number": "AGS-2024-0091",
        "date": date.today() - timedelta(days=3),
    },
    {
        "vendor": "City Medical Suppliers Pvt. Ltd.",
        "amount": "12300.50",
        "currency": "INR",
        "description": "First aid kits and basic medicines for health camp",
        "category": ExpenseCategory.MEDICAL,
        "receipt_number": "CMS-INV-5521",
        "date": date.today() - timedelta(days=7),
    },
    {
        "vendor": "ShikshaKiran Book Depot",
        "amount": "3200.00",
        "currency": "INR",
        "description": "Textbooks and stationery for literacy program",
        "category": ExpenseCategory.EDUCATION,
        "receipt_number": "SKB-0334",
        "date": date.today() - timedelta(days=14),
    },
    {
        "vendor": "Ramesh Transport Services",
        "amount": "6500.00",
        "currency": "INR",
        "description": "Vehicle hire for field visit to flood-affected villages",
        "category": ExpenseCategory.TRANSPORT,
        "receipt_number": "RTS-2024-77",
        "date": date.today() - timedelta(days=5),
    },
    {
        "vendor": "Saral Stationery Mart",
        "amount": "1875.00",
        "currency": "INR",
        "description": "Office supplies: paper, pens, folders",
        "category": ExpenseCategory.SUPPLIES,
        "receipt_number": "SSM-8899",
        "date": date.today() - timedelta(days=10),
    },
    {
        "vendor": "BSNL Telecom",
        "amount": "999.00",
        "currency": "INR",
        "description": "Monthly broadband bill for NGO office",
        "category": ExpenseCategory.COMMUNICATION,
        "receipt_number": "",  # intentionally missing to trigger validation
        "date": date.today() - timedelta(days=1),
    },
    {
        "vendor": "",  # intentionally missing vendor
        "amount": "2100.00",
        "currency": "INR",
        "description": "Miscellaneous field expense",
        "category": ExpenseCategory.OTHER,
        "receipt_number": "MISC-001",
        "date": date.today() - timedelta(days=2),
    },
    {
        "vendor": "Kumar Electricals",
        "amount": "-500.00",  # invalid amount to trigger validation
        "currency": "INR",
        "description": "Electrical repair — incorrect amount on receipt",
        "category": ExpenseCategory.UTILITIES,
        "receipt_number": "KE-2024-15",
        "date": date.today() - timedelta(days=6),
    },
]


def _make_mock_record(filename: str, index: int) -> ExpenseRecord:
    """Create a realistic mock record for a given filename."""
    data = _MOCK_RECEIPTS[index % len(_MOCK_RECEIPTS)].copy()
    return ExpenseRecord(
        source_filename=filename,
        vendor=data["vendor"],
        amount=data["amount"],
        currency=data["currency"],
        description=data["description"],
        category=data["category"],
        receipt_number=data["receipt_number"],
        date=data["date"],
        extraction_mode="mock",
    )


# --------------------------------------------------------------------------- #
# AI extraction via Gemini
# --------------------------------------------------------------------------- #

_EXTRACTION_PROMPT = """
You are a receipt data extraction assistant for an NGO expense management system.

Analyze the provided receipt image and extract the following fields as a JSON object:
{
  "date": "YYYY-MM-DD or empty string if not readable",
  "vendor": "Vendor or shop name, or empty string",
  "amount": "Total amount as a number string (e.g. \"1200.50\"), or empty string",
  "currency": "Currency code (e.g. INR, USD), or INR if not specified",
  "description": "Brief description of what was purchased, or empty string",
  "category": "One of: Food & Nutrition, Medical & Health, Education & Training, Transport & Logistics, Supplies & Materials, Utilities, Salaries & Wages, Rent & Accommodation, Communication, Other, Unknown",
  "receipt_number": "Receipt or invoice number, or empty string"
}

IMPORTANT RULES:
- Do NOT invent information. Use empty string for fields you cannot read.
- Return ONLY valid JSON. No markdown, no explanation text.
- For amount, return only the numeric value (no currency symbols).
- If multiple amounts appear, use the final total.
"""


def _extract_with_gemini(
    image_bytes: bytes,
    filename: str,
    api_key: str,
    model_name: str = "gemini-3.8-flash",
    timeout: int = 30,
) -> ExpenseRecord:
    """Call Gemini Vision API to extract receipt data from image bytes."""
    try:
        import google.generativeai as genai  # noqa: PLC0415

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        # Encode image as base64
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Detect mime type
        mime_type = "image/jpeg"
        if filename.lower().endswith(".png"):
            mime_type = "image/png"

        response = model.generate_content(
            [
                _EXTRACTION_PROMPT,
                {"mime_type": mime_type, "data": b64_image},
            ],
            request_options={"timeout": timeout},
        )

        raw_text = response.text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(
                line for line in lines if not line.startswith("```")
            )

        data = json.loads(raw_text)

        return ExpenseRecord(
            source_filename=filename,
            date=data.get("date") or None,
            vendor=data.get("vendor") or "",
            amount=data.get("amount") or None,
            currency=data.get("currency") or "INR",
            description=data.get("description") or "",
            category=data.get("category") or "Unknown",
            receipt_number=data.get("receipt_number") or "",
            extraction_mode="ai",
        )

    except json.JSONDecodeError as exc:
        logger.warning("Gemini returned non-JSON response for %s: %s", filename, exc)
        return ExpenseRecord(
            source_filename=filename,
            extraction_mode="ai",
            notes=f"AI returned an unreadable response. Please fill in details manually.",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Gemini extraction failed for %s: %s", filename, exc)
        raise


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def extract_receipt(
    image_bytes: bytes,
    filename: str,
    api_key: Optional[str],
    model_name: str = "gemini-3.8-flash",
    file_index: int = 0,
    timeout: int = 30,
) -> tuple[ExpenseRecord, str]:
    """
    Extract receipt data from image bytes.

    Returns:
        (record, mode) where mode is "ai" or "mock"
    """
    if api_key:
        try:
            record = _extract_with_gemini(
                image_bytes, filename, api_key, model_name, timeout
            )
            return record, "ai"
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "AI extraction failed, falling back to mock: %s", exc
            )
            record = _make_mock_record(filename, file_index)
            record.notes = f"AI extraction failed ({type(exc).__name__}). Showing demo data."
            record.extraction_mode = "mock (fallback)"
            return record, "mock (fallback)"
    else:
        record = _make_mock_record(filename, file_index)
        return record, "mock"


def get_demo_records() -> list[ExpenseRecord]:
    """
    Return the full set of demo/mock records for hackathon demonstrations.
    These records intentionally include some valid and some problematic entries.
    """
    records = []
    for i, data in enumerate(_MOCK_RECEIPTS):
        rec = ExpenseRecord(
            source_filename=f"demo_receipt_{i + 1:02d}.jpg",
            vendor=data["vendor"],
            amount=data["amount"],
            currency=data["currency"],
            description=data["description"],
            category=data["category"],
            receipt_number=data["receipt_number"],
            date=data["date"],
            extraction_mode="mock",
        )
        records.append(rec)
    return records
