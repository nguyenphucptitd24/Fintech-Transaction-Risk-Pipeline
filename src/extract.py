import random
from faker import Faker

fake = Faker('vi_VN')

# Sinh số CCCD 12 chữ số ngẫu nhiên
def generate_fake_citizen_id():
    return "".join([str(random.randint(0, 9)) for _ in range(12)])


def _has_null_value(record):
    return any(value is None or (isinstance(value, str) and not value.strip()) for value in record.values())


def _validate_unique(records, key):
    seen = set()
    duplicates = set()
    for record in records:
        value = record.get(key)
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return duplicates


def _validate_customer(customer):
    if _has_null_value(customer):
        return False
    if len(customer.get("citizen_id", "")) != 12:
        return False
    return True


def _validate_account(account):
    if _has_null_value(account):
        return False
    if account.get("balance", 0) <= 0:
        return False
    if account.get("account_type") not in {"SAVINGS", "CHECKING"}:
        return False
    return True


def _validate_transaction(transaction, account_ids):
    if _has_null_value(transaction):
        return False
    if transaction.get("amount", 0) <= 0:
        return False
    if transaction.get("sender_account_id") == transaction.get("receiver_account_id"):
        return False
    if transaction.get("sender_account_id") not in account_ids or transaction.get("receiver_account_id") not in account_ids:
        return False
    return True


def extract_customers(count=50):
    customers = []
    for _ in range(count):
        customer = {
            "citizen_id": generate_fake_citizen_id(),
            "full_name": fake.name(),
            "email": fake.unique.ascii_safe_email(),
            "phone_number": fake.phone_number(),
            "risk_score": random.randint(0, 30),
        }
        if _validate_customer(customer):
            customers.append(customer)

    duplicate_ids = _validate_unique(customers, "citizen_id")
    duplicate_emails = _validate_unique(customers, "email")

    if duplicate_ids or duplicate_emails:
        customers = [c for c in customers if c["citizen_id"] not in duplicate_ids and c["email"] not in duplicate_emails]

    return customers


def extract_accounts(customer_ids):
    accounts = []
    for customer_id in customer_ids:
        for _ in range(random.randint(1, 2)):
            account = {
                "customer_id": customer_id,
                "account_number": fake.unique.bothify("1088#########"),
                "balance": round(random.uniform(100_000, 200_000_000), 3),
                "account_type": random.choice(["SAVINGS", "CHECKING"]),
            }
            if _validate_account(account):
                accounts.append(account)

    duplicate_account_numbers = _validate_unique(accounts, "account_number")
    if duplicate_account_numbers:
        accounts = [a for a in accounts if a["account_number"] not in duplicate_account_numbers]

    return accounts


def extract_transactions(account_ids, count=300):
    types = ["TRANSFER", "WITHDRAWAL", "PAYMENT"]
    transactions = []

    for _ in range(count):
        sender = random.choice(account_ids)
        receiver = random.choice([acc for acc in account_ids if acc != sender])
        transaction = {
            "sender_account_id": sender,
            "receiver_account_id": receiver,
            "amount": round(random.uniform(10_000, 100_000_000), 3),
            "transaction_type": random.choice(types),
            "created_at": fake.date_time_between(start_date="-30d", end_date="now"),
        }
        if _validate_transaction(transaction, account_ids):
            transactions.append(transaction)

    return transactions
