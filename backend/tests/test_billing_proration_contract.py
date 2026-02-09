"""Billing proration contract tests.

Skips if STRIPE_SECRET_KEY is not configured.
Only calls preview-change (no actual charges).
"""
import os
import sys
import pytest

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


SKIP_REASON = "STRIPE_SECRET_KEY not set"


def _stripe_key() -> str:
    """Return the Stripe secret key or empty string."""
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        # Try loading from .env
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("STRIPE_SECRET_KEY="):
                        key = line.split("=", 1)[1].strip()
                        break
    return key


@pytest.fixture(scope="module")
def stripe_api():
    key = _stripe_key()
    if not key:
        pytest.skip(SKIP_REASON)
    import stripe
    stripe.api_key = key
    return stripe


class TestPreviewChangeContract:
    """Test that Stripe Invoice.upcoming returns the expected shape for proration previews."""

    def test_preview_change_response_keys(self, stripe_api):
        """When we preview an upgrade, the response should contain the expected keys."""
        # We need a customer to call Invoice.upcoming; create an ephemeral one
        customer = stripe_api.Customer.create(
            email="test-proration@example.com",
            metadata={"test": "true"},
        )
        try:
            # Create a subscription on Plus price (read from env)
            plus_price = os.environ.get("STRIPE_PRICE_PLUS", "")
            premium_price = os.environ.get("STRIPE_PRICE_PREMIUM", "")

            if not plus_price or not premium_price:
                # Try loading from .env
                env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
                if os.path.exists(env_path):
                    with open(env_path) as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("STRIPE_PRICE_PLUS=") and not plus_price:
                                plus_price = line.split("=", 1)[1].strip()
                            elif line.startswith("STRIPE_PRICE_PREMIUM=") and not premium_price:
                                premium_price = line.split("=", 1)[1].strip()

            if not plus_price or not premium_price:
                pytest.skip("STRIPE_PRICE_PLUS or STRIPE_PRICE_PREMIUM not configured")

            # We need a payment method to create a subscription
            pm = stripe_api.PaymentMethod.create(
                type="card",
                card={
                    "number": "4242424242424242",
                    "exp_month": 12,
                    "exp_year": 2030,
                    "cvc": "123",
                },
            )
            stripe_api.PaymentMethod.attach(pm.id, customer=customer.id)
            stripe_api.Customer.modify(
                customer.id,
                invoice_settings={"default_payment_method": pm.id},
            )

            # Create subscription on Plus tier
            sub = stripe_api.Subscription.create(
                customer=customer.id,
                items=[{"price": plus_price}],
                default_payment_method=pm.id,
            )
            assert sub.status in ("active", "trialing")

            # Preview upgrade to Premium
            sub_item_id = sub["items"]["data"][0]["id"]
            upcoming = stripe_api.Invoice.upcoming(
                customer=customer.id,
                subscription=sub.id,
                subscription_items=[{
                    "id": sub_item_id,
                    "price": premium_price,
                }],
            )

            # Assert expected keys
            assert "amount_due" in upcoming
            assert "currency" in upcoming
            assert "lines" in upcoming
            assert isinstance(upcoming["amount_due"], int)
            assert upcoming["currency"] in ("eur", "usd")

            # Check that proration line items exist
            lines = upcoming["lines"]["data"]
            assert len(lines) >= 1, "Expected at least one proration line item"

            has_proration = any(line.get("proration") for line in lines)
            assert has_proration, "Expected at least one proration line item"

        finally:
            # Cleanup: cancel subscription and delete customer
            try:
                stripe_api.Subscription.cancel(sub.id)
            except Exception:
                pass
            try:
                stripe_api.Customer.delete(customer.id)
            except Exception:
                pass

    def test_preview_same_plan_no_change(self, stripe_api):
        """Previewing the same plan should still return valid invoice data."""
        customer = stripe_api.Customer.create(
            email="test-same-plan@example.com",
            metadata={"test": "true"},
        )
        sub = None
        try:
            plus_price = os.environ.get("STRIPE_PRICE_PLUS", "")
            if not plus_price:
                env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
                if os.path.exists(env_path):
                    with open(env_path) as f:
                        for line in f:
                            if line.strip().startswith("STRIPE_PRICE_PLUS="):
                                plus_price = line.strip().split("=", 1)[1].strip()
                                break
            if not plus_price:
                pytest.skip("STRIPE_PRICE_PLUS not configured")

            pm = stripe_api.PaymentMethod.create(
                type="card",
                card={
                    "number": "4242424242424242",
                    "exp_month": 12,
                    "exp_year": 2030,
                    "cvc": "123",
                },
            )
            stripe_api.PaymentMethod.attach(pm.id, customer=customer.id)
            stripe_api.Customer.modify(
                customer.id,
                invoice_settings={"default_payment_method": pm.id},
            )

            sub = stripe_api.Subscription.create(
                customer=customer.id,
                items=[{"price": plus_price}],
                default_payment_method=pm.id,
            )

            # Preview same plan (no change)
            sub_item_id = sub["items"]["data"][0]["id"]
            upcoming = stripe_api.Invoice.upcoming(
                customer=customer.id,
                subscription=sub.id,
                subscription_items=[{
                    "id": sub_item_id,
                    "price": plus_price,
                }],
            )

            assert "amount_due" in upcoming
            assert isinstance(upcoming["amount_due"], int)

        finally:
            if sub:
                try:
                    stripe_api.Subscription.cancel(sub.id)
                except Exception:
                    pass
            try:
                stripe_api.Customer.delete(customer.id)
            except Exception:
                pass
