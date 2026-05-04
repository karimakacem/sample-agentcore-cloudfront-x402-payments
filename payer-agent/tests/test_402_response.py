"""Tests for 402 response detection and x402 payload extraction."""

import base64
import json
import pytest
from unittest.mock import patch, MagicMock

import httpx

from agent.tools.content import request_content


class Test402ResponseDetection:
    """Tests for detecting and parsing 402 responses."""

    @patch("agent.tools.content.config")
    def test_v1_body_based_detection(self, mock_config):
        """Test v1 detection from response body."""
        mock_config.seller_api_url = "https://example.com"

        payment_info = {
            "x402Version": 1,
            "accepts": [{
                "scheme": "exact",
                "network": "eip155:84532",
                "amount": "1000",
                "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                "payTo": "0xRecipient",
                "maxTimeoutSeconds": 60,
                "extra": {"name": "USDC", "version": "2"},
            }],
        }

        mock_response = MagicMock()
        mock_response.status_code = 402
        mock_response.headers = {}
        mock_response.json.return_value = payment_info

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = request_content("/api/test")

        assert result["http_status"] == 402
        assert result["x402_version"] == 1
        assert result["x402_payload"]["scheme"] == "exact"
        assert result["x402_payload"]["amount"] == "1000"
        assert result["x402_payload"]["payTo"] == "0xRecipient"

    @patch("agent.tools.content.config")
    def test_v2_header_based_detection(self, mock_config):
        """Test v2 detection from PAYMENT-REQUIRED header."""
        mock_config.seller_api_url = "https://example.com"

        payment_info = {
            "x402Version": 2,
            "accepts": [{
                "scheme": "exact",
                "network": "eip155:84532",
                "amount": "2000",
                "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                "payTo": "0xRecipient",
                "resource": "/api/test",
                "description": "Test content",
            }],
        }
        encoded = base64.b64encode(json.dumps(payment_info).encode()).decode()

        mock_response = MagicMock()
        mock_response.status_code = 402
        mock_response.headers = {"PAYMENT-REQUIRED": encoded}
        mock_response.json.return_value = {}

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = request_content("/api/test")

        assert result["http_status"] == 402
        assert result["x402_version"] == 2
        assert result["x402_payload"]["amount"] == "2000"
        assert result["x402_payload"]["resource"] == "/api/test"

    @patch("agent.tools.content.config")
    def test_returns_raw_accepts_payload(self, mock_config):
        """Test that the raw accepts[0] is returned as x402_payload."""
        mock_config.seller_api_url = "https://example.com"

        accepts_entry = {
            "scheme": "exact",
            "network": "eip155:84532",
            "amount": "500",
            "asset": "0xToken",
            "payTo": "0xMerchant",
            "maxTimeoutSeconds": 120,
            "extra": {"name": "USDC", "version": "2"},
            "customField": "preserved",
        }
        payment_info = {"x402Version": 1, "accepts": [accepts_entry]}

        mock_response = MagicMock()
        mock_response.status_code = 402
        mock_response.headers = {}
        mock_response.json.return_value = payment_info

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = request_content("/api/test")

        # The full accepts[0] should be returned as-is
        assert result["x402_payload"] == accepts_entry
        assert result["x402_payload"]["customField"] == "preserved"

    @patch("agent.tools.content.config")
    def test_no_accepts_array(self, mock_config):
        """Test handling when 402 response has no accepts array."""
        mock_config.seller_api_url = "https://example.com"

        mock_response = MagicMock()
        mock_response.status_code = 402
        mock_response.headers = {}
        mock_response.json.return_value = {"x402Version": 1}

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = request_content("/api/test")

        assert result["http_status"] == 402
        assert "error_message" in result

    @patch("agent.tools.content.config")
    def test_backward_compat_payment_required_field(self, mock_config):
        """Test that payment_required dict is still returned for backward compat."""
        mock_config.seller_api_url = "https://example.com"

        payment_info = {
            "x402Version": 1,
            "accepts": [{
                "scheme": "exact",
                "network": "eip155:84532",
                "amount": "1000",
                "asset": "0xToken",
                "payTo": "0xRecipient",
                "extra": {"name": "USDC"},
            }],
        }

        mock_response = MagicMock()
        mock_response.status_code = 402
        mock_response.headers = {}
        mock_response.json.return_value = payment_info

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = request_content("/api/test")

        # Backward-compat summary dict
        assert "payment_required" in result
        assert result["payment_required"]["amount"] == "1000"
        assert result["payment_required"]["recipient"] == "0xRecipient"
        assert result["payment_required"]["currency"] == "USDC"
