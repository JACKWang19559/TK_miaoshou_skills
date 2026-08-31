import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "calculate_tiktok_operations.py"
SPEC = importlib.util.spec_from_file_location("calculate_tiktok_operations", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CalculateTikTokOperationsTests(unittest.TestCase):
    def test_unit_economics_uses_supplied_rates_only(self):
        result = MODULE.calculate_unit(
            {
                "selling_price": 20,
                "product_cost": 5,
                "fulfillment_cost": 2,
                "platform_fee_rate": 0.05,
                "creator_commission_rate": 0.15,
                "ad_cost_rate": 0.10,
                "return_rate": 0.10,
                "return_processing_cost": 1,
                "unrecoverable_return_fraction": 0.20,
            }
        )
        self.assertEqual(result["expected_return_loss"], 0.2)
        self.assertEqual(result["total_variable_cost"], 13.2)
        self.assertEqual(result["contribution_profit"], 6.8)
        self.assertEqual(result["contribution_margin"], 0.34)

    def test_unit_economics_has_no_platform_fee_default(self):
        result = MODULE.calculate_unit({"selling_price": 10, "product_cost": 4})
        self.assertEqual(result["costs"]["platform_charge_cost"], 0)
        self.assertEqual(result["contribution_profit"], 6)

    def test_template_context_drives_dynamic_cost_components(self):
        context = MODULE.normalize_pricing_context(
            {
                "_retrievedAt": "2026-08-12T00:00:00+00:00",
                "data": {
                    "priceTemplateList": [
                        {
                            "priceTemplateId": 9,
                            "site": "US",
                            "name": "US base",
                            "currency": "USD",
                            "profitType": "percent",
                            "profitPercent": 20,
                            "platformChargePercent": 5,
                            "paymentChargePercent": 2,
                            "otherCharge": 1,
                            "logisticsComputeType": "fixed",
                            "logisticsCharge": 3,
                            "snapshotId": 88,
                        }
                    ]
                },
            },
            "template",
            "US",
            template_id=9,
        )
        result = MODULE.calculate_unit(
            {"selling_price": 20, "product_cost": 5, "pricing_context": context}
        )
        self.assertEqual(context["rate_components"]["platform_charge"], 0.05)
        self.assertEqual(context["metadata"]["profitPercent"], 20)
        self.assertEqual(result["costs"]["international_logistics_charge"], 3)
        self.assertEqual(result["total_variable_cost"], 10.4)
        self.assertEqual(result["contribution_profit"], 9.6)
        self.assertEqual(result["pricing_source"]["metadata"]["snapshotId"], 88)

    def test_site_defaults_are_selected_by_exact_site(self):
        context = MODULE.normalize_pricing_context(
            {
                "data": {
                    "tiktokCbSiteAndDefaultChargePercentMap": {
                        "US": {"platformChargePercent": 6, "affiliateChargePercent": 10}
                    },
                    "siteAndDefaultPlatformSupportChargeMap": {"US": 0.5},
                    "siteAndBuyerLogisticDefaultChargeMap": {"US": 4},
                }
            },
            "site_default",
            "US",
        )
        self.assertEqual(context["rate_components"]["platform_charge"], 0.06)
        self.assertEqual(context["rate_components"]["affiliate_charge"], 0.10)
        self.assertEqual(context["amount_components"]["platform_support_charge"], 0.5)
        self.assertNotIn("buyer_logistics_default", context["amount_components"])

    def test_template_target_profit_is_not_counted_as_cost(self):
        context = MODULE.normalize_pricing_context(
            {"data": {"priceTemplateList": [{"priceTemplateId": 1, "site": "US", "currency": "USD", "profitType": "fixed", "fixedProfitAmount": 99}]}},
            "template",
            "US",
            template_id=1,
        )
        result = MODULE.calculate_unit({"selling_price": 10, "product_cost": 4, "pricing_context": context})
        self.assertEqual(result["contribution_profit"], 6)

    def test_price_recommendation_does_not_require_existing_selling_price(self):
        context = {
            "source_type": "template",
            "site": "US",
            "currency": "USD",
            "rate_components": {"platform_charge": 0.05, "payment_charge": 0.03},
            "amount_components": {"logistics_charge": 2},
        }
        result = MODULE.calculate_price(
            {"product_cost": 6, "target_contribution_margin": 0.20, "pricing_context": context}
        )
        self.assertEqual(result["fixed_and_amount_cost"], 8)
        self.assertEqual(result["candidate_price_before_rounding"], 11.11)

    def test_price_recommendation_requires_explicit_target(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            MODULE.calculate_price({"product_cost": 6, "pricing_context": {}})

    def test_inventory_rounds_order_to_moq(self):
        result = MODULE.calculate_inventory(
            {
                "on_hand": 30,
                "on_order": 10,
                "reserved": 5,
                "daily_demand": 5,
                "lead_time_days": 7,
                "review_period_days": 7,
                "safety_days": 3,
                "minimum_order_quantity": 20,
                "unit_landed_cost": 4,
            }
        )
        self.assertEqual(result["available_stock"], 35)
        self.assertEqual(result["stock_cover_days"], 7)
        self.assertEqual(result["reorder_point"], 50)
        self.assertEqual(result["suggested_order_quantity"], 60)
        self.assertEqual(result["estimated_order_cash"], 240)
        self.assertTrue(result["reorder_now"])

    def test_rate_above_one_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            MODULE.calculate_unit(
                {"selling_price": 10, "product_cost": 4, "creator_commission_rate": 1.2}
            )


if __name__ == "__main__":
    unittest.main()
