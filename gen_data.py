from config.database import engine
from src.extract import extract_customers, extract_accounts, extract_transactions
from src.transform import clean_accounts, clean_customers, transform_transactions
from src.load import load_rules, load_customers, load_accounts, load_transactions, truncate_tables


def generate_data():
    with engine.begin() as conn:
        # Xóa sạch dữ liệu cũ và reset khóa chính
        truncate_tables(conn)
        print("🧹 Đã làm sạch dữ liệu cũ.")

        print("🚀 Đang khởi tạo dữ liệu giả lập...")

        load_rules(conn)

        raw_customers = extract_customers(count=50)
        customers = clean_customers(raw_customers)
        customer_ids = load_customers(conn, customers)
        print(f"✅ Đã tạo {len(customer_ids)} khách hàng kèm mã CCCD (citizen_id).")

        raw_accounts = extract_accounts(customer_ids)
        accounts = clean_accounts(raw_accounts)
        account_ids = load_accounts(conn, accounts)
        print(f"✅ Đã tạo {len(account_ids)} tài khoản ngân hàng.")

        raw_transactions = extract_transactions(account_ids, count=300)
        transactions = transform_transactions(raw_transactions, account_ids)
        load_transactions(conn, transactions)
        print("✅ Đã sinh 300 giao dịch mẫu (bao gồm các giao dịch gán nhãn gian lận).")
        print("🎉 Hoàn tất sinh dữ liệu vào Database!")

if __name__ == "__main__":
    generate_data()