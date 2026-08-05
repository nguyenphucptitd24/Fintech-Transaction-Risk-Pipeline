import random
from faker import Faker

fake = Faker('vi_VN')

# Sinh số CCCD 12 chữ số ngẫu nhiên
def generate_fake_citizen_id():
    return "".join([str(random.randint(0, 9)) for _ in range(12)])


def extract_customers(count=50):
    customers = []
    for _ in range(count):
        customers.append(
            {
                "citizen_id": generate_fake_citizen_id(),
                "full_name": fake.name(),
                "email": fake.unique.ascii_safe_email(),
                "phone_number": fake.phone_number(),
                "risk_score": random.randint(0, 30),
            }
        )
    return customers


def extract_accounts(customer_ids):
    accounts = []
    for customer_id in customer_ids:
        for _ in range(random.randint(1, 2)):
            accounts.append(
                {
                    "customer_id": customer_id,
                    "account_number": fake.unique.bothify("1088#########"),
                    "balance": round(random.uniform(100_000, 200_000_000), 3),
                    "account_type": random.choice(["SAVINGS", "CHECKING"]),
                }
            )
    return accounts


def extract_transactions(account_ids, count=300):
    types = ["TRANSFER", "WITHDRAWAL", "PAYMENT"]
    transactions = []

    for _ in range(count):
        sender = random.choice(account_ids)
        receiver = random.choice([acc for acc in account_ids if acc != sender])
        transactions.append(
            {
                "sender_account_id": sender,
                "receiver_account_id": receiver,
                "amount": round(random.uniform(10_000, 100_000_000), 3),
                "transaction_type": random.choice(types),
                "created_at": fake.date_time_between(start_date="-30d", end_date="now"),
            }
        )

    return transactions
