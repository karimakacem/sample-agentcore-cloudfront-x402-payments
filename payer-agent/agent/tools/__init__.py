"""Tools for the x402 payer agent.

This module organizes tools into categories:

1. Service Discovery Tools (Enterprise-Ready):
   - discover_services: Find available paid services from the Gateway
   - request_service: Request any discovered service by name
   - list_approved_services: List pre-approved services for autonomous purchasing
   - check_service_approval: Check if a purchase is pre-approved

2. Core Payment Tools:
   - process_payment: Execute x402 payment via AgentCore Payments ProcessPayment API

3. Content Tools:
   - request_content: Request content from seller API (detects 402 and extracts x402 payload)
   - request_content_with_payment: Retry request with payment proof header
"""

# Service discovery tools (enterprise-ready pattern)
from .discovery import (
    discover_services,
    request_service,
    list_approved_services,
    check_service_approval,
)

# Core payment tool (AgentCore Payments)
from .payment import process_payment

# Content tools
from .content import request_content, request_content_with_payment

# Discovery tools - the enterprise-ready way to find and use services
DISCOVERY_TOOLS = [
    discover_services,
    request_service,
    list_approved_services,
    check_service_approval,
]

# Export core tools as the primary interface
CORE_TOOLS = [
    process_payment,
]

# Content tools
CONTENT_TOOLS = [
    request_content,
    request_content_with_payment,
]

__all__ = [
    # Discovery tools
    "discover_services",
    "request_service",
    "list_approved_services",
    "check_service_approval",
    # Core payment tool
    "process_payment",
    # Content tools
    "request_content",
    "request_content_with_payment",
    # Tool collections
    "DISCOVERY_TOOLS",
    "CORE_TOOLS",
    "CONTENT_TOOLS",
]
