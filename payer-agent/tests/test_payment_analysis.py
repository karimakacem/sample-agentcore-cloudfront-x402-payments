"""Tests for payment analysis.

Note: The analyze_payment tool has been removed in the AgentCore Payments
migration. Session-level budgets (maxSpendAmount) are now enforced server-side
by the ProcessPayment API. This file is kept as a placeholder to document
the change.

The old analyze_payment tool performed:
- Hardcoded threshold checks (amount > 0.01 → reject)
- Balance validation
- Recipient address format validation

All of these are now handled by:
- Session budget enforcement (ProcessPayment rejects over-budget requests)
- AgentCore Payments service-side validation
- The pre-approval list in discovery.py (for UX, not enforcement)
"""

import pytest


class TestPaymentAnalysisMigrated:
    """Verify that old payment analysis tools are removed."""

    def test_analyze_payment_removed(self):
        """Confirm analyze_payment is no longer importable."""
        with pytest.raises(ImportError):
            from agent.tools.payment import analyze_payment

    def test_sign_payment_removed(self):
        """Confirm sign_payment is no longer importable."""
        with pytest.raises(ImportError):
            from agent.tools.payment import sign_payment

    def test_get_wallet_balance_removed(self):
        """Confirm get_wallet_balance is no longer importable."""
        with pytest.raises(ImportError):
            from agent.tools.payment import get_wallet_balance

    def test_request_faucet_funds_removed(self):
        """Confirm request_faucet_funds is no longer importable."""
        with pytest.raises(ImportError):
            from agent.tools.payment import request_faucet_funds

    def test_check_faucet_eligibility_removed(self):
        """Confirm check_faucet_eligibility is no longer importable."""
        with pytest.raises(ImportError):
            from agent.tools.payment import check_faucet_eligibility

    def test_process_payment_exists(self):
        """Confirm process_payment is the new tool."""
        from agent.tools.payment import process_payment
        assert callable(process_payment)
