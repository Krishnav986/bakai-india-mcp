"""Daily Utilities, Safe Math Calculator, and Unit Converter for BAKAI Robot.

Includes Indian Standard Time (IST) clock, AST-based safe math evaluator (zero eval),
and versatile unit conversions supporting standard SI, imperial, and traditional Indian units
(Tola, Seer, Maund, Bigha, Katha, Lakh, Crore).
"""

from __future__ import annotations

import datetime
from typing import Any, Dict
from zoneinfo import ZoneInfo

from core.logging import logger
from core.security import safe_evaluate_math

# Weekday and month names in Hindi
_HINDI_WEEKDAYS = {
    "Monday": "सोमवार",
    "Tuesday": "मंगलवार",
    "Wednesday": "बुधवार",
    "Thursday": "गुरुवार",
    "Friday": "शुक्रवार",
    "Saturday": "शनिवार",
    "Sunday": "रविवार",
}

_HINDI_MONTHS = {
    1: "जनवरी", 2: "फ़रवरी", 3: "मार्च", 4: "अप्रैल",
    5: "मई", 6: "जून", 7: "जुलाई", 8: "अगस्त",
    9: "सितंबर", 10: "अक्टूबर", 11: "नवंबर", 12: "दिसंबर",
}


def get_india_time() -> Dict[str, Any]:
    """Returns the current Indian Standard Time (IST, UTC+05:30), date, and day of the week.

    Tailored for spoken announcements by BAKAI robot.
    """
    try:
        ist_zone = ZoneInfo("Asia/Kolkata")
        now = datetime.datetime.now(ist_zone)
    except Exception:
        # Fallback manual offset (+05:30)
        offset = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        now = datetime.datetime.now(offset)

    weekday_en = now.strftime("%A")
    weekday_hi = _HINDI_WEEKDAYS.get(weekday_en, weekday_en)
    month_hi = _HINDI_MONTHS.get(now.month, str(now.month))

    time_12h = now.strftime("%I:%M %p")
    time_24h = now.strftime("%H:%M:%S")
    date_str = now.strftime("%d %B %Y")

    hour = now.hour
    minute = now.minute

    # Conversational Hindi time phrasing
    period = "सुबह" if 4 <= hour < 12 else "दोपहर" if 12 <= hour < 17 else "शाम" if 17 <= hour < 20 else "रात"
    display_hour = hour % 12
    display_hour = 12 if display_hour == 0 else display_hour
    speech = f"बॉस, अभी भारतीय समय के अनुसार {period} के {display_hour} बजकर {minute} मिनट हो रहे हैं। आज {weekday_hi}, {now.day} {month_hi} {now.year} है।"

    return {
        "status": "success",
        "timezone": "IST (Asia/Kolkata)",
        "utc_offset": "+05:30",
        "time_12h": time_12h,
        "time_24h": time_24h,
        "date": date_str,
        "weekday": weekday_en,
        "weekday_hindi": weekday_hi,
        "iso": now.isoformat(),
        "speech": speech,
    }


def calculator(expression: str) -> Dict[str, Any]:
    """Calculates mathematical expressions securely using AST parsing (no eval).

    Supports basic arithmetic (+, -, *, /, //, %, ^), trigonometry (sin, cos, tan),
    roots (sqrt), logs (log, log10), and constants (pi, e).

    Args:
        expression: Expression to evaluate (e.g. '25 * 40 + 150', 'sqrt(144) + 10^2', 'sin(radians(90))').
    """
    try:
        val = safe_evaluate_math(expression)
        speech = f"बॉस, {expression} का परिणाम {val} है।"
        return {
            "status": "success",
            "expression": expression,
            "result": val,
            "speech": speech,
        }
    except ZeroDivisionError:
        return {
            "status": "math_error",
            "expression": expression,
            "error": "Division by zero is undefined.",
            "speech": "माफ़ कीजिए बॉस, शून्य से विभाजन संभव नहीं है।",
        }
    except Exception as exc:
        return {
            "status": "syntax_error",
            "expression": expression,
            "error": str(exc),
            "speech": f"माफ़ कीजिए बॉस, गणितीय समीकरण समझ नहीं आया: {exc}",
        }


# ----------------------------------------------------------------------
# Unit Conversions
# ----------------------------------------------------------------------

# Conversion multipliers to base units (meters, grams, square meters, bytes)
_LENGTH_TO_METERS = {
    "m": 1.0, "meter": 1.0, "meters": 1.0,
    "km": 1000.0, "kilometer": 1000.0, "kilometers": 1000.0,
    "cm": 0.01, "centimeter": 0.01, "centimeters": 0.01,
    "mm": 0.001, "millimeter": 0.001,
    "mile": 1609.344, "miles": 1609.344,
    "yard": 0.9144, "yards": 0.9144,
    "foot": 0.3048, "feet": 0.3048, "ft": 0.3048,
    "inch": 0.0254, "inches": 0.0254, "in": 0.0254,
}

_WEIGHT_TO_GRAMS = {
    "g": 1.0, "gram": 1.0, "grams": 1.0,
    "kg": 1000.0, "kilogram": 1000.0, "kilograms": 1000.0,
    "mg": 0.001, "milligram": 0.001,
    "lb": 453.59237, "pound": 453.59237, "pounds": 453.59237,
    "oz": 28.349523, "ounce": 28.349523, "ounces": 28.349523,
    # Indian traditional units
    "tola": 11.6638, "tolas": 11.6638,
    "seer": 933.1, "seers": 933.1,
    "maund": 37324.0, "maunds": 37324.0, "mann": 37324.0,
    "quintal": 100000.0, "quintals": 100000.0,
    "tonne": 1000000.0, "ton": 1000000.0,
}

_AREA_TO_SQM = {
    "sqm": 1.0, "square_meter": 1.0, "sq_meters": 1.0,
    "sqft": 0.092903, "square_feet": 0.092903, "sq_feet": 0.092903,
    "acre": 4046.856, "acres": 4046.856,
    "hectare": 10000.0, "hectares": 10000.0,
    "sqkm": 1000000.0,
    # Traditional Indian Land Measurement (Assam / standard)
    "bigha": 1337.8, "bighas": 1337.8,
    "katha": 66.89, "kathas": 66.89,
    "guntha": 101.17, "gunthas": 101.17,
}

_DATA_TO_BYTES = {
    "b": 1, "byte": 1, "bytes": 1,
    "kb": 1024, "kilobyte": 1024,
    "mb": 1024**2, "megabyte": 1024**2,
    "gb": 1024**3, "gigabyte": 1024**3,
    "tb": 1024**4, "terabyte": 1024**4,
}

_INDIAN_NUMERICALS = {
    "lakh": 100_000, "lakhs": 100_000, "lac": 100_000,
    "crore": 10_000_000, "crores": 10_000_000, "cr": 10_000_000,
    "million": 1_000_000, "millions": 1_000_000, "m": 1_000_000,
    "billion": 1_000_000_000, "billions": 1_000_000_000, "b": 1_000_000_000,
    "thousand": 1_000, "k": 1_000,
}


def unit_converter(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    """Converts values between metric, imperial, and traditional Indian units.

    Supports:
    - Temperature (c, f, k)
    - Length (km, m, cm, mm, mile, foot, inch)
    - Weight/Mass (kg, g, mg, lb, tola, seer, maund)
    - Land Area (sqm, sqft, acre, hectare, bigha, katha)
    - Data (b, kb, mb, gb, tb)
    - Number scale (lakh, crore, million, billion)

    Args:
        value: Numeric quantity to convert (e.g. 10.5).
        from_unit: Source unit (e.g. 'c', 'tola', 'bigha', 'crore', 'km').
        to_unit: Target unit (e.g. 'f', 'gram', 'sqft', 'million', 'mile').
    """
    fu = from_unit.strip().lower()
    tu = to_unit.strip().lower()

    # Temperature
    if fu in ("c", "celsius") and tu in ("f", "fahrenheit"):
        res = (value * 9 / 5) + 32
        res = round(res, 2)
        speech = f"बॉस, {value}°C बराबर {res}°F होता है।"
        return {"status": "success", "value": value, "from_unit": fu, "to_unit": tu, "result": res, "speech": speech}
    if fu in ("f", "fahrenheit") and tu in ("c", "celsius"):
        res = (value - 32) * 5 / 9
        res = round(res, 2)
        speech = f"बॉस, {value}°F बराबर {res}°C होता है।"
        return {"status": "success", "value": value, "from_unit": fu, "to_unit": tu, "result": res, "speech": speech}
    if fu in ("c", "celsius") and tu in ("k", "kelvin"):
        res = round(value + 273.15, 2)
        speech = f"बॉस, {value}°C बराबर {res} K होता है।"
        return {"status": "success", "value": value, "from_unit": fu, "to_unit": tu, "result": res, "speech": speech}

    # Length
    if fu in _LENGTH_TO_METERS and tu in _LENGTH_TO_METERS:
        in_meters = value * _LENGTH_TO_METERS[fu]
        res = round(in_meters / _LENGTH_TO_METERS[tu], 4)
        speech = f"बॉस, {value} {fu} बराबर {res} {tu} होता है।"
        return {"status": "success", "value": value, "from_unit": fu, "to_unit": tu, "result": res, "speech": speech}

    # Weight / Mass
    if fu in _WEIGHT_TO_GRAMS and tu in _WEIGHT_TO_GRAMS:
        in_grams = value * _WEIGHT_TO_GRAMS[fu]
        res = round(in_grams / _WEIGHT_TO_GRAMS[tu], 4)
        speech = f"बॉस, {value} {fu} बराबर {res} {tu} होता है।"
        return {"status": "success", "value": value, "from_unit": fu, "to_unit": tu, "result": res, "speech": speech}

    # Area
    if fu in _AREA_TO_SQM and tu in _AREA_TO_SQM:
        in_sqm = value * _AREA_TO_SQM[fu]
        res = round(in_sqm / _AREA_TO_SQM[tu], 4)
        speech = f"बॉस, {value} {fu} बराबर {res} {tu} होता है।"
        return {"status": "success", "value": value, "from_unit": fu, "to_unit": tu, "result": res, "speech": speech}

    # Data Storage
    if fu in _DATA_TO_BYTES and tu in _DATA_TO_BYTES:
        in_bytes = value * _DATA_TO_BYTES[fu]
        res = round(in_bytes / _DATA_TO_BYTES[tu], 4)
        speech = f"बॉस, {value} {fu} बराबर {res} {tu} होता है।"
        return {"status": "success", "value": value, "from_unit": fu, "to_unit": tu, "result": res, "speech": speech}

    # Indian Numericals (Lakh, Crore, Million, Billion)
    if fu in _INDIAN_NUMERICALS and tu in _INDIAN_NUMERICALS:
        total = value * _INDIAN_NUMERICALS[fu]
        res = round(total / _INDIAN_NUMERICALS[tu], 4)
        speech = f"बॉस, {value} {fu} बराबर {res} {tu} होता है (कुल संख्या: {int(total):,}।)"
        return {"status": "success", "value": value, "from_unit": fu, "to_unit": tu, "result": res, "total_number": int(total), "speech": speech}

    return {
        "status": "unsupported_conversion",
        "from_unit": fu,
        "to_unit": tu,
        "speech": f"माफ़ कीजिए बॉस, {fu} से {tu} में परिवर्तन समर्थित नहीं है।",
    }
