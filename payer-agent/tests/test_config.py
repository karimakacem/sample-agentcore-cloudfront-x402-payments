"""Tests for the agent configuration module."""

import os
from unittest.mock import patch

from agent.config import AgentConfig


class TestAgentConfig:
    """Tests for AgentConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = AgentConfig()

        assert config.model_id == "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        assert config.aws_region == "us-west-2"
        assert config.payment_manager_arn == ""
        assert config.payment_session_id == ""
        assert config.payment_instrument_id == ""
        assert config.process_payment_role_arn == ""
        assert config.user_id == ""
        assert config.dp_endpoint == ""
        assert config.seller_api_url == ""

    def test_from_env_with_defaults(self):
        """Test from_env uses defaults when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = AgentConfig.from_env()

            assert config.model_id == "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
            assert config.aws_region == "us-west-2"
            assert config.payment_manager_arn == ""

    def test_from_env_with_custom_values(self):
        """Test from_env reads environment variables correctly."""
        env_vars = {
            "BEDROCK_MODEL_ID": "anthropic.claude-3-haiku",
            "AWS_REGION": "us-east-1",
            "MANAGER_ARN": "arn:aws:bedrock-agentcore:us-west-2:123:payment-manager/mgr-1",
            "PAYMENT_SESSION_ID": "session-abc",
            "PAYMENT_INSTRUMENT_ID": "instrument-xyz",
            "PROCESS_PAYMENT_ROLE_ARN": "arn:aws:iam::123:role/ProcessPaymentRole",
            "USER_ID": "user-test-123",
            "DP_ENDPOINT": "https://custom-endpoint.example.com",
            "SELLER_API_URL": "https://api.example.com",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = AgentConfig.from_env()

            assert config.model_id == "anthropic.claude-3-haiku"
            assert config.aws_region == "us-east-1"
            assert config.payment_manager_arn == "arn:aws:bedrock-agentcore:us-west-2:123:payment-manager/mgr-1"
            assert config.payment_session_id == "session-abc"
            assert config.payment_instrument_id == "instrument-xyz"
            assert config.process_payment_role_arn == "arn:aws:iam::123:role/ProcessPaymentRole"
            assert config.user_id == "user-test-123"
            assert config.dp_endpoint == "https://custom-endpoint.example.com"
            assert config.seller_api_url == "https://api.example.com"

    def test_cdp_fields_removed(self):
        """Test that old CDP fields no longer exist."""
        config = AgentConfig()
        assert not hasattr(config, "cdp_api_key_name")
        assert not hasattr(config, "cdp_api_key_private_key")
        assert not hasattr(config, "cdp_wallet_secret")
        assert not hasattr(config, "cdp_wallet_address")
        assert not hasattr(config, "network_id")
