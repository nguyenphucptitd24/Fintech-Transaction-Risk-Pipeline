import logging
import re
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("transform")

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


def normalize_account_ids(account_ids):
    if account_ids is None:
        return set()
    if isinstance(account_ids, set):
        return account_ids
    return set(account_ids)


def _validate_transaction(transaction, account_ids):
    account_id_set = normalize_account_ids(account_ids)
    if _has_null_value(transaction):
        return False
    if transaction.get("amount") is None or transaction.get("amount", 0) <= 0:
        return False
    if not isinstance(transaction.get("created_at"), datetime):
        return False
    if transaction.get("sender_account_id") == transaction.get("receiver_account_id"):
        return False
    if transaction.get("sender_account_id") not in account_id_set or transaction.get("receiver_account_id") not in account_id_set:
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


def _calculate_window_features(transaction, history):
    created_at = transaction.get("created_at")
    if not isinstance(created_at, datetime):
        return {
            "avg_amount_30d": 0.0,
            "amount_vs_avg_30d_ratio": 0.0,
            "tx_count_30d": 0,
            "recent_tx_count_1m": 0,
            "velocity_tx_count_1m": 1,
            "unique_locations_30d": 0,
            "unique_devices_30d": 0,
        }

    cutoff_30d = created_at - timedelta(days=30)
    cutoff_1m = created_at - timedelta(minutes=1)

    recent_30d = [
        item for item in history
        if isinstance(item.get("created_at"), datetime)
        and item["created_at"] >= cutoff_30d
        and item["created_at"] <= created_at
    ]

    tx_count_30d = len(recent_30d)
    avg_amount_30d = 0.0
    if tx_count_30d:
        avg_amount_30d = round(sum(item.get("amount", 0.0) or 0.0 for item in recent_30d) / tx_count_30d, 3)

    amount_vs_avg_30d_ratio = 0.0
    if avg_amount_30d > 0:
        amount_vs_avg_30d_ratio = round(transaction.get("amount", 0.0) / avg_amount_30d, 3)

    recent_1m = [
        item for item in recent_30d
        if isinstance(item.get("created_at"), datetime)
        and item["created_at"] >= cutoff_1m
    ]

    unique_locations_30d = len({item.get("location") for item in recent_30d if item.get("location")})
    unique_devices_30d = len({item.get("device_id") for item in recent_30d if item.get("device_id")})

    return {
        "avg_amount_30d": avg_amount_30d,
        "amount_vs_avg_30d_ratio": amount_vs_avg_30d_ratio,
        "tx_count_30d": tx_count_30d,
        "recent_tx_count_1m": len(recent_1m),
        "velocity_tx_count_1m": len(recent_1m) + 1,
        "unique_locations_30d": unique_locations_30d,
        "unique_devices_30d": unique_devices_30d,
    }


def transform_transactions(raw_transactions, account_ids):
    normalized_transactions = []
    account_id_set = normalize_account_ids(account_ids)
    dropped_transactions = 0
    flagged_transactions = 0

    for tx in raw_transactions:
        normalized_amount = _normalize_amount(tx.get("amount"))
        normalized_created_at = _normalize_datetime(tx.get("created_at"))
        cleaned_tx = {
            **tx,
            "amount": normalized_amount,
            "created_at": normalized_created_at,
        }
        if not _validate_transaction(cleaned_tx, account_id_set):
            dropped_transactions += 1
            logger.warning(
                "Dropped transaction due to validation failure: sender=%s receiver=%s amount=%s created_at=%s",
                cleaned_tx.get("sender_account_id"),
                cleaned_tx.get("receiver_account_id"),
                cleaned_tx.get("amount"),
                cleaned_tx.get("created_at"),
            )
            continue
        normalized_transactions.append(cleaned_tx)

    normalized_transactions.sort(key=lambda tx: tx.get("created_at") or datetime.min)

    transformed = []
    history_by_account = {}
    for tx in normalized_transactions:
        sender_account_id = tx.get("sender_account_id")
        history = history_by_account.setdefault(sender_account_id, [])
        features = _calculate_window_features(tx, history)
        risk_reasons = evaluate_risk_rules(tx, features)
        fraud_flag = bool(risk_reasons)
        if fraud_flag:
            flagged_transactions += 1
            logger.info(
                "Flagged transaction: sender=%s receiver=%s amount=%s reasons=%s",
                tx.get("sender_account_id"),
                tx.get("receiver_account_id"),
                tx.get("amount"),
                risk_reasons,
            )
        transformed.append(
            {
                **tx,
                **features,
                "is_fraud": fraud_flag,
                "risk_reasons": risk_reasons,
                "status": transaction_status(fraud_flag),
            }
        )
        history.append(tx)

    logger.info(
        "Transform completed: input=%s valid=%s dropped=%s flagged=%s",
        len(raw_transactions),
        len(transformed),
        dropped_transactions,
        flagged_transactions,
    )
    return transformed


def evaluate_risk_rules(transaction, features):
    reasons = []

    amount = transaction.get("amount") or 0.0
    if amount > 50_000_000.0:
        reasons.append("HIGH_AMOUNT_TRANSFER")

    if features.get("velocity_tx_count_1m", 0) >= 5:
        reasons.append("SUSPICIOUS_RAPID_TX")

    if features.get("amount_vs_avg_30d_ratio", 0.0) >= 10.0:
        reasons.append("UNUSUAL_AMOUNT_RATIO")

    location = transaction.get("location")
    if location and features.get("unique_locations_30d", 0) >= 3:
        reasons.append("UNUSUAL_LOCATION_PATTERN")

    device_id = transaction.get("device_id")
    if device_id and features.get("unique_devices_30d", 0) >= 3:
        reasons.append("UNUSUAL_DEVICE_PATTERN")

    if transaction.get("transaction_type") == "TRANSFER" and amount >= 10_000_000.0 and features.get("tx_count_30d", 0) >= 3:
        reasons.append("MULTI_ACCOUNT_TRANSFER_PATTERN")

    return reasons


def transaction_status(is_fraud_flag, statuses=None):
    if is_fraud_flag:
        return "FLAGGED"

    if statuses is None:
        return "SUCCESS"
    return statuses[0] if statuses else "SUCCESS"
