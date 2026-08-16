from sqlalchemy import text


def truncate_tables(conn):
    conn.execute(
        text("TRUNCATE TABLE transactions, accounts, customers RESTART IDENTITY CASCADE;")
    )


def load_rules(conn):
    conn.execute(
        text(
            """
            INSERT INTO fraud_rules (rule_name, description, threshold_amount) VALUES 
            ('HIGH_AMOUNT_TRANSFER', 'Giao dịch chuyển tiền giá trị lớn bất thường', 50000000.000),
            ('SUSPICIOUS_RAPID_TX', 'Nhiều giao dịch liên tiếp trong thời gian ngắn', 10000000.000)
            ON CONFLICT (rule_name) DO NOTHING;
            """
        )
    )


def load_customers(conn, customers, batch_size: int = 1000):
    """Insert customers in batches and return list of generated customer_ids.

    Uses executemany under the hood by passing a list of dicts to
    ``conn.execute(text(stmt), chunk)`` which is efficient for bulk inserts.
    """
    customer_ids = []
    if not customers:
        return customer_ids

    stmt = text(
        """
        INSERT INTO customers (citizen_id, full_name, email, phone_number, risk_score)
        VALUES (:citizen_id, :full_name, :email, :phone_number, :risk_score)
        RETURNING customer_id;
        """
    )

    for i in range(0, len(customers), batch_size):
        chunk = customers[i : i + batch_size]
        result = conn.execute(stmt, chunk)
        rows = result.fetchall()
        customer_ids.extend([row[0] for row in rows])

    return customer_ids


def load_accounts(conn, accounts):
    account_ids = []
    if not accounts:
        return account_ids

    stmt = text(
        """
        INSERT INTO accounts (customer_id, account_number, balance, account_type)
        VALUES (:customer_id, :account_number, :balance, :account_type)
        RETURNING account_id;
        """
    )

    batch_size = 1000
    for i in range(0, len(accounts), batch_size):
        chunk = accounts[i : i + batch_size]
        result = conn.execute(stmt, chunk)
        rows = result.fetchall()
        account_ids.extend([row[0] for row in rows])

    return account_ids


def load_transactions(conn, transactions):
    if not transactions:
        return

    stmt = text(
        """
        INSERT INTO transactions (
            sender_account_id,
            receiver_account_id,
            amount,
            transaction_type,
            status,
            is_fraud,
            created_at
        ) VALUES (
            :sender_account_id,
            :receiver_account_id,
            :amount,
            :transaction_type,
            :status,
            :is_fraud,
            :created_at
        );
        """
    )

    batch_size = 1000
    for i in range(0, len(transactions), batch_size):
        chunk = transactions[i : i + batch_size]
        conn.execute(stmt, chunk)
