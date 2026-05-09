"""Tests for request_content_with_payment retry and header construction."""

import base64
import json
import pytest
from unittest.mock import patch, MagicMock, call

from agent.tools.content import request_content_with_payment
from agent.tools.payment import _last_payment_context


class TestRetryWithPayment:
    """Tests for the request_content_with_payment tool."""

    def setup_method(self):
        _last_payment_context.clear()

    @patch("agent.tools.content.config")
    def test_no_proof_returns_error(self, mock_config):
        """Test that calling without a prior process_payment returns error."""
        mock_config.seller_api_url = "https://example.com"

        result = request_content_with_payment("/api/test")

        assert result["http_status"] == 0
        assert "No payment proof" in result["error_message"]

    @patch("agent.tools.content.config")
    def test_v1_uses_x_payment_header(self, mock_config):
        """Test that v1 constructs X-PAYMENT header correctly."""
        mock_config.seller_api_url = "https://example.com"

        # Set up payment context (simulating a successful process_payment)
        _last_payment_context["proof"] = {
            "payload": {"signature": "0xabc", "authorization": {"from": "0x1"}}
        }
        _last_payment_context["x402_version"] = 1
        _last_payment_context["x402_payload"] = {
            "scheme": "exact",
            "network": "eip155:84532",
            "amount": "1000",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {"content": "paid data"}

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = request_content_with_payment("/api/test")

        assert result["http_status"] == 200

        # Verify X-PAYMENT header was sent
        call_kwargs = mock_client.post.call_args.kwargs
        assert "X-PAYMENT" in call_kwargs["headers"]

        # Decode and verify header structure
        header_value = call_kwargs["headers"]["X-PAYMENT"]
        decoded = json.loads(base64.b64decode(header_value))
        assert decoded["x402Version"] == 1  # Must be int, not string
        assert decoded["scheme"] == "exact"
        assert decoded["network"] == "eip155:84532"
        assert "payload" in decoded

    @patch("agent.tools.content.config")
    def test_v2_uses_payment_signature_header(self, mock_config):
        """Test that v2 constructs PAYMENT-SIGNATURE header correctly."""
        mock_config.seller_api_url = "https://example.com"

        _last_payment_context["proof"] = {
            "payload": {"signature": "0xdef", "authorization": {"from": "0x2"}}
        }
        _last_payment_context["x402_version"] = 2
        _last_payment_context["x402_payload"] = {
            "scheme": "exact",
            "network": "eip155:84532",
            "amount": "2000",
            "resource": "/api/premium",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {"content": "premium data"}

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = request_content_with_payment("/api/premium")

        assert result["http_status"] == 200

        call_kwargs = mock_client.post.call_args.kwargs
        assert "PAYMENT-SIGNATURE" in call_kwargs["headers"]

        header_value = call_kwargs["headers"]["PAYMENT-SIGNATURE"]
        decoded = json.loads(base64.b64decode(header_value))
        assert decoded["x402Version"] == 2  # Must be int, not string
        assert decoded["resource"] == "/api/premium"
        assert "accepted" in decoded
        assert "payload" in decoded
        assert "extension" in decoded

    @patch("agent.tools.content.config")
    def test_retries_on_402(self, mock_config):
        """Test exponential backoff retry when merchant returns 402."""
        mock_config.seller_api_url = "https://example.com"

        _last_payment_context["proof"] = {"payload": {"signature": "0x"}}
        _last_payment_context["x402_version"] = 1
        _last_payment_context["x402_payload"] = {"scheme": "exact", "network": "eip155:84532"}

        # First two calls return 402, third returns 200
        mock_402 = MagicMock()
        mock_402.status_code = 402
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.headers = {}
        mock_200.json.return_value = {"content": "data"}

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.side_effect = [mock_402, mock_402, mock_200]

            with patch("time.sleep"):  # Don't actually sleep in tests
                result = request_content_with_payment("/api/test")

        assert result["http_status"] == 200
        assert mock_client.post.call_count == 3

    @patch("agent.tools.content.config")
    def test_uses_post_method(self, mock_config):
        """Test that retry uses POST method (paid endpoints expect POST)."""
        mock_config.seller_api_url = "https://example.com"

        _last_payment_context["proof"] = {"payload": {"signature": "0x"}}
        _last_payment_context["x402_version"] = 1
        _last_payment_context["x402_payload"] = {"scheme": "exact", "network": "eip155:84532"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {}

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            request_content_with_payment("/api/test")

        # Should use POST
        mock_client.post.assert_called_once()

    @patch("agent.tools.content.config")
    def test_x402_version_is_integer_in_header(self, mock_config):
        """Test that x402Version in the header is an integer, not a string."""
        mock_config.seller_api_url = "https://example.com"

        for version in [1, 2]:
            _last_payment_context["proof"] = {"payload": {"sig": "0x"}}
            _last_payment_context["x402_version"] = version
            _last_payment_context["x402_payload"] = {"scheme": "exact", "network": "eip155:84532"}

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.json.return_value = {}

            with patch("httpx.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client_cls.return_value.__enter__.return_value = mock_client
                mock_client.post.return_value = mock_response

                request_content_with_payment("/api/test")

            call_kwargs = mock_client.post.call_args.kwargs
            header_name = "X-PAYMENT" if version == 1 else "PAYMENT-SIGNATURE"
            header_value = call_kwargs["headers"][header_name]
            decoded = json.loads(base64.b64decode(header_value))
            # CRITICAL: must be int, not string
            assert isinstance(decoded["x402Version"], int)
            assert decoded["x402Version"] == version
