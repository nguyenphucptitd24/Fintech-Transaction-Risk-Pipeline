import unittest
from datetime import datetime

from src.transform import transform_transactions


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


if __name__ == "__main__":
    unittest.main()
