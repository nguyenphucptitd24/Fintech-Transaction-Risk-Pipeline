DROP TABLE IF EXISTS transactions, accounts, fraud_rules, customers CASCADE;
-- 1. Bảng Khách hàng (Customers)
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    citizen_id VARCHAR(12) UNIQUE NOT NULL,      -- Số CCCD/CMND (12 chữ số)
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone_number VARCHAR(20),
    risk_score INT DEFAULT 0 CHECK (risk_score BETWEEN 0 AND 100), -- Điểm rủi ro từ 0 - 100
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_citizen_id_length CHECK (LENGTH(citizen_id) = 12)
);

-- 2. Bảng Tài khoản (Accounts)
CREATE TABLE IF NOT EXISTS accounts (
    account_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    account_number VARCHAR(20) UNIQUE NOT NULL,
    balance DECIMAL(15, 3) DEFAULT 0.000 CHECK (balance >= 0), -- Khóa tài khoản bị âm tiền
    account_type VARCHAR(20) DEFAULT 'CHECKING' CHECK (account_type IN ('SAVINGS', 'CHECKING', 'CREDIT')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Bảng Giao dịch (Transactions)
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id SERIAL PRIMARY KEY,
    sender_account_id INT REFERENCES accounts(account_id),
    receiver_account_id INT REFERENCES accounts(account_id),
    amount DECIMAL(15, 3) NOT NULL CHECK (amount > 0), -- Số tiền giao dịch phải lớn hơn 0
    transaction_type VARCHAR(30) NOT NULL CHECK (transaction_type IN ('TRANSFER', 'WITHDRAWAL', 'PAYMENT', 'DEPOSIT')),
    status VARCHAR(20) DEFAULT 'SUCCESS' CHECK (status IN ('SUCCESS', 'FAILED', 'PENDING', 'FLAGGED')),
    is_fraud BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ràng buộc không thể tự chuyển tiền cho chính mình cùng 1 tài khoản
    CONSTRAINT chk_different_accounts CHECK (sender_account_id <> receiver_account_id)
);

-- 4. Bảng Quy tắc Cảnh báo Gian lận (Fraud Rules)
CREATE TABLE IF NOT EXISTS fraud_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    threshold_amount DECIMAL(15, 3) CHECK (threshold_amount >= 0),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Tối ưu lọc giao dịch theo mốc thời gian và trạng thái gian lận
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_is_fraud ON transactions(is_fraud) WHERE is_fraud = TRUE;

-- Tối ưu truy vết dòng tiền gửi/nhận (Phân tích mạng lưới giao dịch)
CREATE INDEX IF NOT EXISTS idx_transactions_sender ON transactions(sender_account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_receiver ON transactions(receiver_account_id);

-- Tối ưu tra cứu tài khoản nhanh theo CCCD (Data Analytics / KYC lookup)
CREATE INDEX IF NOT EXISTS idx_customers_citizen_id ON customers(citizen_id);