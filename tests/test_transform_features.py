import unittest
from datetime import datetime, timedelta

from src.transform import transform_transactions, normalize_account_ids


class TransformFeatureEngineeringTest(unittest.TestCase):
    def test_transform_adds_rolling_transaction_features(self):
        raw_transactions = [
            {
                "sender_account_id": 1,
                "receiver_account_id": 2,
                "amount": 1000.0,
                "transaction_type": "TRANSFER",
                "created_at": datetime(2024, 1, 1, 10, 0, 0),
            },
            {
                "sender_account_id": 1,
                "receiver_account_id": 2,
                "amount": 2000.0,
                "transaction_type": "TRANSFER",
                "created_at": datetime(2024, 1, 1, 10, 0, 30),
            },
        ]

        transformed = transform_transactions(raw_transactions, [1, 2])

        self.assertEqual(len(transformed), 2)
        self.assertEqual(transformed[0]["avg_amount_30d"], 0.0)
        self.assertEqual(transformed[0]["amount_vs_avg_30d_ratio"], 0.0)
        self.assertEqual(transformed[0]["tx_count_30d"], 0)
        self.assertEqual(transformed[0]["recent_tx_count_1m"], 0)

        self.assertEqual(transformed[1]["avg_amount_30d"], 1000.0)
        self.assertEqual(transformed[1]["amount_vs_avg_30d_ratio"], 2.0)
        self.assertEqual(transformed[1]["tx_count_30d"], 1)
        self.assertEqual(transformed[1]["recent_tx_count_1m"], 1)

    def test_transform_uses_rule_based_risk_engine(self):
        raw_transactions = [
            {
                "sender_account_id": 1,
                "receiver_account_id": 2,
                "amount": 60_000_000.0,
                "transaction_type": "TRANSFER",
                "created_at": datetime(2024, 1, 1, 10, 0, 0),
            },
            {
                "sender_account_id": 1,
                "receiver_account_id": 2,
                "amount": 5000.0,
                "transaction_type": "TRANSFER",
                "created_at": datetime(2024, 1, 1, 10, 0, 30),
            },
        ]

        transformed = transform_transactions(raw_transactions, [1, 2])

        self.assertTrue(transformed[0]["is_fraud"])
        self.assertEqual(transformed[0]["risk_reasons"], ["HIGH_AMOUNT_TRANSFER"])
        self.assertEqual(transformed[0]["status"], "FLAGGED")

        self.assertFalse(transformed[1]["is_fraud"])
        self.assertEqual(transformed[1]["risk_reasons"], [])
        self.assertEqual(transformed[1]["status"], "SUCCESS")

    def test_transform_flags_unusual_location_device_and_transfer_patterns(self):
        raw_transactions = [
            {
                "sender_account_id": 1,
                "receiver_account_id": 2,
                "amount": 15_000_000.0,
                "transaction_type": "TRANSFER",
                "location": "HCM",
                "device_id": "device_a",
                "created_at": datetime(2024, 1, 1, 10, 0, 0),
            },
            {
                "sender_account_id": 1,
                "receiver_account_id": 3,
                "amount": 12_000_000.0,
                "transaction_type": "TRANSFER",
                "location": "HN",
                "device_id": "device_b",
                "created_at": datetime(2024, 1, 1, 10, 1, 0),
            },
            {
                "sender_account_id": 1,
                "receiver_account_id": 4,
                "amount": 11_000_000.0,
                "transaction_type": "TRANSFER",
                "location": "DN",
                "device_id": "device_c",
                "created_at": datetime(2024, 1, 1, 10, 2, 0),
            },
            {
                "sender_account_id": 1,
                "receiver_account_id": 5,
                "amount": 10_000_000.0,
                "transaction_type": "TRANSFER",
                "location": "CT",
                "device_id": "device_d",
                "created_at": datetime(2024, 1, 1, 10, 3, 0),
            },
        ]

        transformed = transform_transactions(raw_transactions, [1, 2, 3, 4, 5])

        self.assertTrue(transformed[-1]["is_fraud"])
        self.assertIn("UNUSUAL_LOCATION_PATTERN", transformed[-1]["risk_reasons"])
        self.assertIn("UNUSUAL_DEVICE_PATTERN", transformed[-1]["risk_reasons"])
        self.assertIn("MULTI_ACCOUNT_TRANSFER_PATTERN", transformed[-1]["risk_reasons"])

    def test_transform_flags_velocity_burst_transactions(self):
        raw_transactions = []
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        for index in range(5):
            raw_transactions.append(
                {
                    "sender_account_id": 1,
                    "receiver_account_id": index + 2,
                    "amount": 2_000_000.0,
                    "transaction_type": "TRANSFER",
                    "created_at": base_time + timedelta(seconds=index * 10),
                }
            )

        transformed = transform_transactions(raw_transactions, [1, 2, 3, 4, 5, 6])

        self.assertTrue(transformed[-1]["is_fraud"])
        self.assertIn("SUSPICIOUS_RAPID_TX", transformed[-1]["risk_reasons"])

    def test_normalize_account_ids_uses_hash_lookup(self):
        self.assertEqual(normalize_account_ids([1, 2, 3]), {1, 2, 3})
        self.assertEqual(normalize_account_ids({3, 4}), {3, 4})


if __name__ == "__main__":
    unittest.main()
