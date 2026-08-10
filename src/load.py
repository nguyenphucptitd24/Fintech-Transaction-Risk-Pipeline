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


def load_customers(conn, customers):
    customer_ids = []
    for customer in customers:
        result = conn.execute(
            text(
                """
                INSERT INTO customers (citizen_id, full_name, email, phone_number, risk_score)
                VALUES (:citizen_id, :full_name, :email, :phone_number, :risk_score)
                RETURNING customer_id;
                """
            ),
            customer,
        )
        customer_ids.append(result.scalar())
    return customer_ids


def load_accounts(conn, accounts):
    account_ids = []
    for account in accounts:
        result = conn.execute(
            text(
                """
                INSERT INTO accounts (customer_id, account_number, balance, account_type)
                VALUES (:customer_id, :account_number, :balance, :account_type)
                RETURNING account_id;
                """
            ),
            account,
        )
        account_ids.append(result.scalar())
    return account_ids


def load_transactions(conn, transactions):
    for transaction in transactions:
        conn.execute(
            text(
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
            ),
            transaction,
        )
