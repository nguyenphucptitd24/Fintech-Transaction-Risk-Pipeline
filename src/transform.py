import random
import re
from datetime import datetime

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_valid_email(email):
    return bool(email and EMAIL_PATTERN.match(email))


def _has_null_value(record):
    return any(value is None or (isinstance(value, str) and not value.strip()) for value in record.values())


def _is_valid_phone(phone):
    return bool(phone and re.match(r"^\+84\d{9}$", phone))


def _normalize_phone_number(phone):
    if not phone:
        return None

    digits = "".join(re.findall(r"\d+", phone))
    if not digits:
        return None

    if digits.startswith("84") and len(digits) == 11:
        return "+84" + digits[2:]
    if digits.startswith("0") and len(digits) == 10:
        return "+84" + digits[1:]
    if len(digits) == 9:
        return "+84" + digits
    if len(digits) == 10:
        return "+84" + digits[1:]

    return "+" + digits


def _normalize_balance(balance):
    try:
        return round(abs(float(balance)), 3)
    except (TypeError, ValueError):
        return None


def _normalize_amount(amount):
    try:
        return round(abs(float(amount)), 3)
    except (TypeError, ValueError):
        return None


def _normalize_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _validate_customer(customer):
    if _has_null_value(customer):
        return False
    if not _is_valid_email(customer.get("email")):
        return False
    if not _is_valid_phone(customer.get("phone_number")):
        return False
    if len(customer.get("citizen_id", "")) != 12:
        return False
    return True


def _validate_account(account):
    if _has_null_value(account):
        return False
    if account.get("balance") is None or account.get("balance", 0) <= 0:
        return False
    if account.get("account_type") not in {"SAVINGS", "CHECKING"}:
        return False
    return True


def _validate_transaction(transaction, account_ids):
    if _has_null_value(transaction):
        return False
    if transaction.get("amount") is None or transaction.get("amount", 0) <= 0:
        return False
    if not isinstance(transaction.get("created_at"), datetime):
        return False
    if transaction.get("sender_account_id") == transaction.get("receiver_account_id"):
        return False
    if transaction.get("sender_account_id") not in account_ids or transaction.get("receiver_account_id") not in account_ids:
        return False
    return True


def clean_customers(raw_customers):
    cleaned = []
    for customer in raw_customers:
        normalized_phone = _normalize_phone_number(customer.get("phone_number"))
        cleaned_customer = {**customer, "phone_number": normalized_phone}
        if _validate_customer(cleaned_customer):
            cleaned.append(cleaned_customer)
    return cleaned


def clean_accounts(raw_accounts):
    cleaned = []
    for account in raw_accounts:
        normalized_balance = _normalize_balance(account.get("balance"))
        cleaned_account = {**account, "balance": normalized_balance}
        if _validate_account(cleaned_account):
            cleaned.append(cleaned_account)
    return cleaned


def transform_transactions(raw_transactions, account_ids):
    transformed = []
    for tx in raw_transactions:
        normalized_amount = _normalize_amount(tx.get("amount"))
        normalized_created_at = _normalize_datetime(tx.get("created_at"))
        cleaned_tx = {
            **tx,
            "amount": normalized_amount,
            "created_at": normalized_created_at,
        }
        if not _validate_transaction(cleaned_tx, account_ids):
            continue
        fraud_flag = is_fraud(cleaned_tx["amount"])
        transformed.append(
            {
                **cleaned_tx,
                "is_fraud": fraud_flag,
                "status": transaction_status(fraud_flag),
            }
        )
    return transformed


def is_fraud(amount, threshold=50_000_000.0):
    return amount > threshold and random.random() < 0.7


def transaction_status(is_fraud_flag, statuses=None):
    if is_fraud_flag:
        return "FLAGGED"

    if statuses is None:
        statuses = ["SUCCESS", "SUCCESS", "SUCCESS", "FAILED"]
    return random.choice(statuses)
