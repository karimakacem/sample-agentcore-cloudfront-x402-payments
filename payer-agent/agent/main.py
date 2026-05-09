"""Main agent definition for the x402 payer agent.

This module defines the payer agent that handles x402 payment flows
using Amazon Bedrock AgentCore Payments.

ENTERPRISE-READY ARCHITECTURE:
The agent uses dynamic service discovery instead of hardcoded tools:
1. discover_services: Find available paid services from the Gateway
2. request_service: Access any discovered service by name
3. process_payment: Execute payments via AgentCore Payments ProcessPayment API
4. Autonomous purchasing with pre-approval lists + session budget enforcement
"""

from typing import Callable, Optional

from strands import Agent
from strands.models import BedrockModel

from .config import config
from .tracing import init_tracing, get_tracer
from .tools.payment import process_payment
from .tools.discovery import (
    discover_services,
    request_service,
    list_approved_services,
    check_service_approval,
)
from .tools.content import (
    request_content,
    request_content_with_payment,
)
from .mcp_client import MCPClient, discover_mcp_tools, get_mcp_client

# Core tools that are always available to the agent
CORE_TOOLS = [
    # Service Discovery (Enterprise-Ready)
    discover_services,
    request_service,
    list_approved_services,
    check_service_approval,
    # Payment Tool (AgentCore Payments)
    process_payment,
    # Content tools
    request_content,
    request_content_with_payment,
]

SYSTEM_PROMPT = """You are an AI payment agent that helps users access paid services using the x402 protocol.
You process payments via Amazon Bedrock AgentCore Payments — a managed service that handles
wallet management and transaction signing server-side. You operate under ProcessPaymentRole
with a pre-set session budget and CANNOT create sessions, instruments, or override limits.

## Your Tools

### Service Discovery Tools (USE THESE FIRST)
- discover_services: Find all available paid services from the Gateway.
- request_service: Request any discovered service by name. Returns x402_payload on 402.
- list_approved_services: See which services are pre-approved for autonomous purchasing.
- check_service_approval: Check if a specific purchase is pre-approved.

### Payment Tool
- process_payment: Execute an x402 payment via AgentCore Payments ProcessPayment API.
  Pass the x402_payload from a 402 response AS-IS. Do NOT parse individual fields.

### Content Tools
- request_content: Request content from the seller API. Returns x402_payload on 402.
- request_content_with_payment: Retry with payment proof after process_payment succeeds.

## Payment Flow (Three Steps)

When an endpoint returns HTTP 402 (Payment Required):

1. **Detect 402**: Call request_content(url) or request_service(name).
   The response includes x402_payload and x402_version.

2. **Pay**: Call process_payment(x402_payload=<the x402_payload>, x402_version=<version>).
   Pass x402_payload AS-IS — do not reconstruct or cherry-pick fields.
   Wait for status: "PROOF_GENERATED".

3. **Retry**: Call request_content_with_payment(url) or request_service(name) again.
   The payment proof is automatically attached. Includes retry with backoff
   for on-chain settlement.

That's it — three tool calls.

## Important Rules

- ALWAYS pass x402_payload from the 402 response directly to process_payment.
  The API accepts the raw merchant payload. Do NOT parse individual fields.
- The x402_version from the 402 response tells process_payment how to handle the payload.
- After process_payment succeeds, the proof is stored internally — just call the
  retry tool with the URL.
- Session budget (maxSpendAmount) is enforced server-side. If you exceed the budget,
  ProcessPayment will reject the request.
- For pre-approved services, proceed automatically. For others, ask the user first.
- Always report the payment amount to the user before paying.

## Workflow Examples

User: "What services are available?"
→ Call discover_services() and present the list with prices.

User: "Get me the premium article"
→ request_content("/api/premium-article") → gets 402 with x402_payload
→ process_payment(x402_payload=..., x402_version=...) → PROOF_GENERATED
→ request_content_with_payment("/api/premium-article") → 200 with content

User: "I want the research report"
→ request_service("get_research_report") → gets 402
→ Check approval, ask user if not pre-approved
→ process_payment(...) → request_service("get_research_report") again → content

## Transparency Requirements
Always be transparent about:
- What services are available (use discover_services)
- Payment amounts and what they're for
- Whether a purchase was automatic (pre-approved) or required confirmation
- Transaction details after successful payments
- Any errors or issues encountered
"""


def create_payer_agent(
    additional_tools: Optional[list[Callable]] = None,
    custom_system_prompt: Optional[str] = None,
) -> Agent:
    """Create and configure the x402 payer agent.

    Args:
        additional_tools: Optional list of additional tools to add to the agent.
                         These are typically MCP-discovered content tools.
        custom_system_prompt: Optional custom system prompt to override the default.

    Returns:
        Configured Agent instance with core payment tools and any additional tools.
    """
    # Initialize tracing
    init_tracing(
        service_name="x402-payer-agent",
        enable_console_export=config.otel_console_export,
    )

    model = BedrockModel(
        model_id=config.model_id,
        region_name=config.aws_region,
    )

    # Combine core tools with any additional (MCP-discovered) tools
    tools = list(CORE_TOOLS)
    if additional_tools:
        tools.extend(additional_tools)

    agent = Agent(
        model=model,
        tools=tools,
        system_prompt=custom_system_prompt or SYSTEM_PROMPT,
    )

    return agent


async def create_payer_agent_with_mcp(
    gateway_url: Optional[str] = None,
    custom_system_prompt: Optional[str] = None,
    force_discovery: bool = False,
) -> Agent:
    """Create a payer agent with MCP-discovered tools.

    This function discovers tools from the Gateway MCP endpoint and
    creates an agent with both core payment tools and discovered content tools.

    Args:
        gateway_url: Optional Gateway URL for MCP discovery.
                    Uses config.seller_api_url if not provided.
        custom_system_prompt: Optional custom system prompt.
        force_discovery: Force tool discovery even if cached.

    Returns:
        Configured Agent instance with core and MCP-discovered tools.

    Raises:
        RuntimeError: If MCP tool discovery fails.
    """
    # Discover MCP tools
    mcp_tools = await discover_mcp_tools(
        gateway_url=gateway_url,
        force_refresh=force_discovery,
    )

    # Create agent with discovered tools
    return create_payer_agent(
        additional_tools=mcp_tools,
        custom_system_prompt=custom_system_prompt,
    )


def get_core_tools() -> list[Callable]:
    """Get the list of core payment tools.

    Returns:
        List of core tool functions.
    """
    return list(CORE_TOOLS)


async def run_agent(user_message: str, additional_tools: Optional[list[Callable]] = None) -> str:
    """Run the agent with a user message and return the response.

    Args:
        user_message: The user's input message.
        additional_tools: Optional list of additional tools (e.g., MCP-discovered tools).

    Returns:
        The agent's response as a string.
    """
    agent = create_payer_agent(additional_tools=additional_tools)
    tracer = get_tracer()

    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("agent.message_length", len(user_message))
        span.set_attribute("agent.core_tools_count", len(CORE_TOOLS))
        span.set_attribute("agent.additional_tools_count", len(additional_tools) if additional_tools else 0)
        response = agent(user_message)
        span.set_attribute("agent.response_length", len(str(response)))
        return str(response)


async def run_agent_with_mcp(
    user_message: str,
    gateway_url: Optional[str] = None,
    force_discovery: bool = False,
) -> str:
    """Run the agent with MCP-discovered tools.

    Args:
        user_message: The user's input message.
        gateway_url: Optional Gateway URL for MCP discovery.
        force_discovery: Force tool discovery even if cached.

    Returns:
        The agent's response as a string.

    Raises:
        RuntimeError: If MCP tool discovery fails.
    """
    agent = await create_payer_agent_with_mcp(
        gateway_url=gateway_url,
        force_discovery=force_discovery,
    )
    tracer = get_tracer()

    mcp_client = get_mcp_client()
    mcp_tools_count = len(mcp_client.get_strands_tools())

    with tracer.start_as_current_span("agent.run_with_mcp") as span:
        span.set_attribute("agent.message_length", len(user_message))
        span.set_attribute("agent.core_tools_count", len(CORE_TOOLS))
        span.set_attribute("agent.mcp_tools_count", mcp_tools_count)
        response = agent(user_message)
        span.set_attribute("agent.response_length", len(str(response)))
        return str(response)


# Entry point for local testing
if __name__ == "__main__":
    import asyncio

    async def main():
        print("x402 Payer Agent initializing...")
        print("Core tools: process_payment, discover_services, request_service")
        print(f"Payment Manager: {config.payment_manager_arn}")
        print(f"Session: {config.payment_session_id}")

        try:
            mcp_tools = await discover_mcp_tools()
            print(f"Discovered {len(mcp_tools)} MCP tools")
            for t in mcp_tools:
                print(f"  - {t.__name__}")
            agent = create_payer_agent(additional_tools=mcp_tools)
        except Exception as e:
            print(f"MCP discovery failed: {e}")
            print("Running with core tools only.")
            agent = create_payer_agent()

        print("-" * 50)
        print("Type 'quit' to exit.")

        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() == "quit":
                break
            response = agent(user_input)
            print(f"\nAgent: {response}")

    asyncio.run(main())
