"""
Pytest configuration and fixtures for payer-agent tests.

This module provides shared fixtures for testing the payer agent,
including the Gateway target mock for local testing without
requiring deployed infrastructure.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.mocks import GatewayTargetMock, GatewayTargetMockConfig


# ============================================================================
# Gateway Target Mock Fixtures
# ============================================================================

@pytest.fixture
def gateway_mock_config() -> GatewayTargetMockConfig:
    """Create a Gateway target mock configuration."""
    return GatewayTargetMockConfig(
        base_url="https://mock-gateway.example.com",
        default_price_usdc="1000",
        default_network="eip155:84532",
        default_asset="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        default_recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
    )


@pytest.fixture
def gateway_mock(gateway_mock_config: GatewayTargetMockConfig) -> GatewayTargetMock:
    """Create a Gateway target mock for testing."""
    return GatewayTargetMock(config=gateway_mock_config)


@pytest.fixture
def mcp_client_with_mock(gateway_mock: GatewayTargetMock):
    """Create an MCP client configured to use the Gateway mock."""
    from agent.mcp_client import MCPClient

    client = MCPClient(
        gateway_url=gateway_mock.config.base_url,
        cache_ttl_seconds=60,
        enable_caching=False,
    )
    return client


# ============================================================================
# AgentCore Payments Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_dp_client():
    """Create a mock boto3 bedrock-agentcore data plane client.

    Returns a MagicMock configured to simulate ProcessPayment responses.
    """
    client = MagicMock()

    # Default: successful ProcessPayment response
    client.process_payment.return_value = {
        "status": "PROOF_GENERATED",
        "paymentOutput": {
            "cryptoX402": {
                "payload": {
                    "signature": "0x" + "ab" * 65,
                    "authorization": {
                        "from": "0x1111111111111111111111111111111111111111",
                        "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
                        "value": "1000",
                        "validAfter": "1700000000",
                        "validBefore": "1700000060",
                        "nonce": "0x" + "cd" * 32,
                    },
                },
            },
        },
        "ResponseMetadata": {"RequestId": "test-request-id"},
    }

    return client


@pytest.fixture
def mock_sts_client():
    """Create a mock STS client for role assumption."""
    client = MagicMock()
    client.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
            "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "SessionToken": "FwoGZXIvYXdzEBYaDHqa0AP",
            "Expiration": "2025-01-01T00:00:00Z",
        }
    }
    return client


@pytest.fixture
def sample_x402_payload_v1():
    """Sample x402 v1 payment requirement (accepts[0] from merchant)."""
    return {
        "scheme": "exact",
        "network": "eip155:84532",
        "amount": "1000",
        "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        "maxTimeoutSeconds": 60,
        "extra": {
            "name": "USDC",
            "version": "2",
        },
    }


@pytest.fixture
def sample_x402_payload_v2():
    """Sample x402 v2 payment requirement (accepts[0] from merchant)."""
    return {
        "scheme": "exact",
        "network": "eip155:84532",
        "amount": "2000",
        "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        "maxTimeoutSeconds": 60,
        "extra": {
            "name": "USDC",
            "version": "2",
        },
        "resource": "/api/premium-article",
        "description": "Premium article access",
        "mimeType": "application/json",
        "outputSchema": {"type": "object"},
    }


@pytest.fixture
def sample_process_payment_response():
    """Sample successful ProcessPayment API response."""
    return {
        "status": "PROOF_GENERATED",
        "paymentOutput": {
            "cryptoX402": {
                "payload": {
                    "signature": "0x" + "ab" * 65,
                    "authorization": {
                        "from": "0x1111111111111111111111111111111111111111",
                        "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
                        "value": "1000",
                        "validAfter": "1700000000",
                        "validBefore": "1700000060",
                        "nonce": "0x" + "cd" * 32,
                    },
                },
            },
        },
    }


# ============================================================================
# Environment-based Fixtures
# ============================================================================

@pytest.fixture
def seller_api_url() -> str:
    """Get the seller API URL from environment."""
    url = os.environ.get("SELLER_API_URL")
    if not url:
        pytest.skip("SELLER_API_URL not set - skipping integration tests")
    return url


@pytest.fixture
def gateway_api_url() -> str:
    """Get the Gateway API URL from environment."""
    url = os.environ.get("GATEWAY_API_URL")
    if not url:
        pytest.skip("GATEWAY_API_URL not set - skipping integration tests")
    return url


# ============================================================================
# Mock HTTP Client Fixtures
# ============================================================================

@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx.AsyncClient for testing."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        yield mock_instance


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires deployed infrastructure)",
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running",
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests by default."""
    if config.getoption("--run-integration", default=False):
        return

    skip_integration = pytest.mark.skip(
        reason="Integration tests skipped. Use --run-integration to run."
    )

    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires deployed infrastructure)",
    )
