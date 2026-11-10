"""Security utilities for BAKAI India MCP Server.

Provides SSRF prevention, URL validation against safe allowlists, safe AST-based
mathematical evaluation (no eval), and input sanitization to guard against prompt injection.
"""

from __future__ import annotations

import ast
import ipaddress
import math
import re
import socket
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

# Private / reserved IPv4 & IPv6 networks
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.88.99.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
    ipaddress.ip_network("::1/128"),      # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),     # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),    # IPv6 Link-Local
]

# Allowlist for safe website opening
SAFE_WEBSITE_DOMAINS: Set[str] = {
    # Indian E-commerce & Shopping
    "amazon.in",
    "www.amazon.in",
    "flipkart.com",
    "www.flipkart.com",
    "myntra.com",
    "www.myntra.com",
    "blinkit.com",
    "www.blinkit.com",
    "zeptonow.com",
    "www.zeptonow.com",
    "swiggy.com",
    "www.swiggy.com",
    "zomato.com",
    "www.zomato.com",
    # Media & Entertainment
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "spotify.com",
    "open.spotify.com",
    "music.youtube.com",
    "jiosaavn.com",
    "www.jiosaavn.com",
    "gaana.com",
    "www.gaana.com",
    # News & Information
    "newsonair.gov.in",
    "prasarbharati.gov.in",
    "ddnews.gov.in",
    "thehindu.com",
    "www.thehindu.com",
    "ndtv.com",
    "www.ndtv.com",
    "timesofindia.indiatimes.com",
    "assamtribune.com",
    "www.assamtribune.com",
    "pratidintime.com",
    "www.pratidintime.com",
    "wikipedia.org",
    "en.wikipedia.org",
    "hi.wikipedia.org",
    "as.wikipedia.org",
    "bbc.com",
    "www.bbc.com",
    # Core Tech & Utilities
    "google.com",
    "www.google.com",
    "google.co.in",
    "www.google.co.in",
    "mail.google.com",
    "maps.google.com",
    "irctc.co.in",
    "www.irctc.co.in",
    "digilocker.gov.in",
    "india.gov.in",
    "uidai.gov.in",
    "npci.org.in",
    "github.com",
    "www.github.com",
}


def validate_safe_url(url: str, allowed_schemes: Tuple[str, ...] = ("http", "https")) -> Tuple[bool, str]:
    """Validates an external URL to protect against SSRF and malicious protocol handlers.

    Returns:
        (is_safe, error_or_canonical_url)
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception as exc:
        return False, f"Malformed URL: {exc}"

    if parsed.scheme.lower() not in allowed_schemes:
        return False, f"Prohibited URL scheme '{parsed.scheme}'. Only {allowed_schemes} allowed."

    host = parsed.hostname
    if not host:
        return False, "URL is missing a valid hostname"

    # Check for localhost variants
    if host.lower() in ("localhost", "0.0.0.0", "127.0.0.1", "::1"):
        return False, "Access to localhost/loopback addresses is forbidden"

    # Check IP addresses directly
    try:
        ip = ipaddress.ip_address(host)
        for net in _BLOCKED_NETWORKS:
            if ip in net:
                return False, f"IP address {ip} belongs to private or forbidden network {net}"
    except ValueError:
        # Not a raw IP; host is a domain name
        pass

    return True, url


def is_domain_allowed(url: str, allowed_domains: Set[str] = SAFE_WEBSITE_DOMAINS) -> bool:
    """Verifies if the URL belongs to an approved domain or sub-domain."""
    is_safe, _ = validate_safe_url(url)
    if not is_safe:
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in allowed_domains)


# ----------------------------------------------------------------------
# Safe Mathematical Evaluation (AST-based, Zero eval())
# ----------------------------------------------------------------------

_SAFE_MATH_OPERATORS: Dict[type, Any] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a**b if abs(b) <= 1000 else (_ for _ in ()).throw(ValueError("Exponent too large")),
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: +a,
}

_SAFE_MATH_FUNCTIONS: Dict[str, Any] = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "radians": math.radians,
    "degrees": math.degrees,
    "factorial": lambda n: math.factorial(int(n)) if int(n) <= 100 else (_ for _ in ()).throw(ValueError("Factorial input too large")),
}

_SAFE_MATH_CONSTANTS: Dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}


def safe_evaluate_math(expression: str) -> float | int:
    """Evaluates mathematical expressions safely using Python's AST.

    Guarantees no arbitrary code execution, no import execution, no attribute
    lookup, and strictly limits exponents and factorials to prevent DoS.
    """
    if not expression or not expression.strip():
        raise ValueError("Expression cannot be empty")

    cleaned = expression.strip().replace("^", "**").replace("×", "*").replace("÷", "/")

    try:
        node = ast.parse(cleaned, mode="eval")
    except SyntaxError as err:
        raise ValueError(f"Invalid math syntax: {err}") from err

    def _eval(node_elem: ast.AST) -> float | int:
        if isinstance(node_elem, ast.Expression):
            return _eval(node_elem.body)
        if isinstance(node_elem, ast.Constant):
            if isinstance(node_elem.value, (int, float)):
                return node_elem.value
            raise ValueError(f"Unsupported constant type: {type(node_elem.value)}")
        if isinstance(node_elem, ast.BinOp):
            left = _eval(node_elem.left)
            right = _eval(node_elem.right)
            op_type = type(node_elem.op)
            if op_type in _SAFE_MATH_OPERATORS:
                if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                    raise ZeroDivisionError("Division by zero")
                return _SAFE_MATH_OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        if isinstance(node_elem, ast.UnaryOp):
            operand = _eval(node_elem.operand)
            op_type = type(node_elem.op)
            if op_type in _SAFE_MATH_OPERATORS:
                return _SAFE_MATH_OPERATORS[op_type](operand)
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        if isinstance(node_elem, ast.Call):
            if isinstance(node_elem.func, ast.Name):
                func_name = node_elem.func.id.lower()
                if func_name in _SAFE_MATH_FUNCTIONS:
                    args = [_eval(a) for a in node_elem.args]
                    return _SAFE_MATH_FUNCTIONS[func_name](*args)
            raise ValueError(f"Function call not permitted: {ast.dump(node_elem.func)}")
        if isinstance(node_elem, ast.Name):
            name = node_elem.id.lower()
            if name in _SAFE_MATH_CONSTANTS:
                return _SAFE_MATH_CONSTANTS[name]
            raise ValueError(f"Unknown variable or constant: '{node_elem.id}'")
        raise ValueError(f"Unsupported expression construct: {type(node_elem).__name__}")

    result = _eval(node)
    # Return int if clean integer
    if isinstance(result, float) and result.is_integer() and abs(result) < 1e15:
        return int(result)
    return result


def sanitize_external_text(text: str, max_chars: int = 2500) -> str:
    """Sanitizes text fetched from untrusted websites to prevent prompt injection.

    Removes system instruction delimiters, control tokens, and caps length.
    """
    if not text:
        return ""

    # Truncate
    cleaned = text[:max_chars]

    # Strip dangerous tokens that attempt to spoof assistant / system directives
    forbidden_tokens = [
        "<|im_start|>",
        "<|im_end|>",
        "<|system|>",
        "[SYSTEM_INSTRUCTION]",
        "[INSTRUCTION]",
        "BEGIN INSTRUCTION",
        "IGNORE ALL PREVIOUS INSTRUCTIONS",
    ]
    for token in forbidden_tokens:
        cleaned = re.sub(re.escape(token), "", cleaned, flags=re.IGNORECASE)

    return cleaned.strip()
