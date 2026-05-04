"""Tests for the process_payment tool (AgentCore Payments)."""

import pytest
from unittest.mock import patch, MagicMock

from agent.tools.payment import process_payment, _last_payment_context, get_last_payment_context


class TestProcessPayment:
    """Tests for the process_payment tool."""

    def setup_method(self):
        """Clear payment context before each test."""
        _last_payment_context.clear()

    @patch("agent.tools.payment._get_dp_client")
    def test_process_payment_v1_success(self, mock_get_client, sample_x402_payload_v1, mock_dp_client):
        """Test successful v1 payment processing."""
        mock_get_client.return_value = mock_dp_client

        result = process_payment(
            x402_payload=sample_x402_payload_v1,
            x402_version=1,
        )

        assert result["status"] == "PROOF_GENERATED"
        assert "paymentOutput" in result
        assert "ResponseMetadata" not in result  # Should be stripped

        # Verify ProcessPayment was called with correct params
        call_kwargs = mock_dp_client.process_payment.call_args.kwargs
        assert call_kwargs["paymentType"] == "CRYPTO_X402"
        assert call_kwargs["paymentInput"]["cryptoX402"]["version"] == "1"
        # v1: full payload passed through (no stripping)
        payload = call_kwargs["paymentInput"]["cryptoX402"]["payload"]
        assert payload["scheme"] == "exact"
        assert payload["network"] == "eip155:84532"
        assert "clientToken" in call_kwargs

    @patch("agent.tools.payment._get_dp_client")
    def test_process_payment_v2_strips_metadata(self, mock_get_client, sample_x402_payload_v2, mock_dp_client):
        """Test that v2 strips non-payment metadata fields."""
        mock_get_client.return_value = mock_dp_client

        result = process_payment(
            x402_payload=sample_x402_payload_v2,
            x402_version=2,
        )

        assert result["status"] == "PROOF_GENERATED"

        # Verify metadata fields were stripped for v2
        call_kwargs = mock_dp_client.process_payment.call_args.kwargs
        payload = call_kwargs["paymentInput"]["cryptoX402"]["payload"]
        assert "description" not in payload
        assert "mimeType" not in payload
        assert "resource" not in payload
        assert "outputSchema" not in payload
        # Payment fields should remain
        assert payload["scheme"] == "exact"
        assert payload["amount"] == "2000"
        assert payload["payTo"] == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"

    @patch("agent.tools.payment._get_dp_client")
    def test_process_payment_stores_proof(self, mock_get_client, sample_x402_payload_v1, mock_dp_client):
        """Test that proof is stored in module state after success."""
        mock_get_client.return_value = mock_dp_client

        process_payment(x402_payload=sample_x402_payload_v1, x402_version=1)

        ctx = get_last_payment_context()
        assert "proof" in ctx
        assert ctx["x402_version"] == 1
        assert ctx["x402_payload"] == sample_x402_payload_v1

    @patch("agent.tools.payment._get_dp_client")
    def test_process_payment_failure(self, mock_get_client, sample_x402_payload_v1):
        """Test handling of ProcessPayment API errors."""
        mock_client = MagicMock()
        mock_client.process_payment.side_effect = Exception("Budget exceeded")
        mock_get_client.return_value = mock_client

        result = process_payment(x402_payload=sample_x402_payload_v1, x402_version=1)

        assert result["status"] == "ERROR"
        assert "Budget exceeded" in result["error"]

    @patch("agent.tools.payment._get_dp_client")
    def test_process_payment_non_proof_status(self, mock_get_client, sample_x402_payload_v1):
        """Test handling when ProcessPayment returns non-PROOF_GENERATED status."""
        mock_client = MagicMock()
        mock_client.process_payment.return_value = {
            "status": "FAILED",
            "error": "Insufficient funds",
            "ResponseMetadata": {"RequestId": "test"},
        }
        mock_get_client.return_value = mock_client

        result = process_payment(x402_payload=sample_x402_payload_v1, x402_version=1)

        assert result["status"] == "FAILED"
        # Proof should NOT be stored
        ctx = get_last_payment_context()
        assert "proof" not in ctx

    @patch("agent.tools.payment._get_dp_client")
    def test_process_payment_includes_client_token(self, mock_get_client, sample_x402_payload_v1, mock_dp_client):
        """Test that clientToken UUID is included for idempotency."""
        mock_get_client.return_value = mock_dp_client

        process_payment(x402_payload=sample_x402_payload_v1, x402_version=1)

        call_kwargs = mock_dp_client.process_payment.call_args.kwargs
        assert "clientToken" in call_kwargs
        # Should be a valid UUID format
        import uuid
        uuid.UUID(call_kwargs["clientToken"])  # Raises if invalid
