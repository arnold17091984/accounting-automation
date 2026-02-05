-- =============================================================================
-- Accounting Automation System - Merchant Seed Data
-- =============================================================================
-- Initial merchant → category mappings for common vendors
-- Run after schema.sql
-- =============================================================================

-- Clear existing data (for development only - remove in production)
-- TRUNCATE merchant_lookup RESTART IDENTITY;

-- -----------------------------------------------------------------------------
-- Utilities & Services
-- -----------------------------------------------------------------------------
INSERT INTO merchant_lookup (merchant_pattern, account_code, account_name, category, confidence, source) VALUES
-- Telecommunications
('PLDT', '6310', 'Telecommunications', 'expense', 1.00, 'manual'),
('GLOBE TELECOM', '6310', 'Telecommunications', 'expense', 1.00, 'manual'),
('SMART COMMUNICATIONS', '6310', 'Telecommunications', 'expense', 1.00, 'manual'),
('CONVERGE ICT', '6310', 'Telecommunications', 'expense', 1.00, 'manual'),

-- Utilities
('MERALCO', '6320', 'Utilities - Electricity', 'expense', 1.00, 'manual'),
('MANILA WATER', '6321', 'Utilities - Water', 'expense', 1.00, 'manual'),
('MAYNILAD', '6321', 'Utilities - Water', 'expense', 1.00, 'manual'),

-- Internet & Software
('GOOGLE.*CLOUD', '6350', 'Cloud Services', 'expense', 0.95, 'manual'),
('AMAZON WEB SERVICES', '6350', 'Cloud Services', 'expense', 1.00, 'manual'),
('AWS', '6350', 'Cloud Services', 'expense', 0.90, 'manual'),
('MICROSOFT', '6351', 'Software Subscriptions', 'expense', 0.90, 'manual'),
('ADOBE', '6351', 'Software Subscriptions', 'expense', 1.00, 'manual'),
('CANVA', '6351', 'Software Subscriptions', 'expense', 1.00, 'manual'),
('ZOOM', '6351', 'Software Subscriptions', 'expense', 1.00, 'manual'),
('SLACK', '6351', 'Software Subscriptions', 'expense', 1.00, 'manual')
ON CONFLICT (merchant_pattern) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Office & Supplies
-- -----------------------------------------------------------------------------
INSERT INTO merchant_lookup (merchant_pattern, account_code, account_name, category, confidence, source) VALUES
('NATIONAL BOOK STORE', '6210', 'Office Supplies', 'expense', 1.00, 'manual'),
('OFFICE WAREHOUSE', '6210', 'Office Supplies', 'expense', 1.00, 'manual'),
('FULLY BOOKED', '6210', 'Office Supplies', 'expense', 0.85, 'manual'),
('SM OFFICE', '6210', 'Office Supplies', 'expense', 0.80, 'manual'),
('STAPLES', '6210', 'Office Supplies', 'expense', 1.00, 'manual')
ON CONFLICT (merchant_pattern) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Transportation & Fuel
-- -----------------------------------------------------------------------------
INSERT INTO merchant_lookup (merchant_pattern, account_code, account_name, category, confidence, source) VALUES
-- Fuel
('SHELL', '6410', 'Fuel & Gas', 'company_car', 1.00, 'manual'),
('PETRON', '6410', 'Fuel & Gas', 'company_car', 1.00, 'manual'),
('CALTEX', '6410', 'Fuel & Gas', 'company_car', 1.00, 'manual'),
('PHOENIX PETROLEUM', '6410', 'Fuel & Gas', 'company_car', 1.00, 'manual'),
('SEAOIL', '6410', 'Fuel & Gas', 'company_car', 1.00, 'manual'),
('UNIOIL', '6410', 'Fuel & Gas', 'company_car', 1.00, 'manual'),
('TOTAL.*GAS', '6410', 'Fuel & Gas', 'company_car', 0.95, 'manual'),

-- Transportation Services
('GRAB', '6420', 'Transportation', 'expense', 0.95, 'manual'),
('GRABCAR', '6420', 'Transportation', 'expense', 1.00, 'manual'),
('GRABFOOD', '6230', 'Meals & Entertainment', 'expense', 1.00, 'manual'),
('ANGKAS', '6420', 'Transportation', 'expense', 1.00, 'manual'),
('JOYRIDE', '6420', 'Transportation', 'expense', 1.00, 'manual'),

-- Parking & Tolls
('EASYTRIP', '6430', 'Tolls & Parking', 'company_car', 1.00, 'manual'),
('AUTOSWEEP', '6430', 'Tolls & Parking', 'company_car', 1.00, 'manual'),
('NLEX', '6430', 'Tolls & Parking', 'company_car', 1.00, 'manual'),
('SLEX', '6430', 'Tolls & Parking', 'company_car', 1.00, 'manual'),
('PARKING', '6430', 'Tolls & Parking', 'company_car', 0.85, 'manual'),

-- Vehicle Maintenance
('TOYOTA', '6440', 'Vehicle Maintenance', 'company_car', 0.90, 'manual'),
('HONDA CARS', '6440', 'Vehicle Maintenance', 'company_car', 0.90, 'manual'),
('MOTOLITE', '6440', 'Vehicle Maintenance', 'company_car', 1.00, 'manual'),
('GOODYEAR', '6440', 'Vehicle Maintenance', 'company_car', 1.00, 'manual'),
('BRIDGESTONE', '6440', 'Vehicle Maintenance', 'company_car', 1.00, 'manual')
ON CONFLICT (merchant_pattern) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Meals & Entertainment
-- -----------------------------------------------------------------------------
INSERT INTO merchant_lookup (merchant_pattern, account_code, account_name, category, confidence, source) VALUES
-- Fast Food
('JOLLIBEE', '6230', 'Meals & Entertainment', 'expense', 0.95, 'manual'),
('MCDONALDS', '6230', 'Meals & Entertainment', 'expense', 0.95, 'manual'),
('KFC', '6230', 'Meals & Entertainment', 'expense', 0.95, 'manual'),
('CHOWKING', '6230', 'Meals & Entertainment', 'expense', 0.95, 'manual'),
('MANG INASAL', '6230', 'Meals & Entertainment', 'expense', 0.95, 'manual'),
('GREENWICH', '6230', 'Meals & Entertainment', 'expense', 0.95, 'manual'),
('PIZZA HUT', '6230', 'Meals & Entertainment', 'expense', 0.95, 'manual'),
('SHAKEYS', '6230', 'Meals & Entertainment', 'expense', 0.95, 'manual'),

-- Coffee Shops
('STARBUCKS', '6230', 'Meals & Entertainment', 'expense', 0.95, 'manual'),
('COFFEE BEAN', '6230', 'Meals & Entertainment', 'expense', 0.95, 'manual'),
('BO''S COFFEE', '6230', 'Meals & Entertainment', 'expense', 0.95, 'manual'),
('TIM HORTONS', '6230', 'Meals & Entertainment', 'expense', 0.95, 'manual'),

-- Delivery
('FOODPANDA', '6230', 'Meals & Entertainment', 'expense', 1.00, 'manual'),
('PICK A ROO', '6230', 'Meals & Entertainment', 'expense', 1.00, 'manual')
ON CONFLICT (merchant_pattern) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Banks & Financial Services
-- -----------------------------------------------------------------------------
INSERT INTO merchant_lookup (merchant_pattern, account_code, account_name, category, confidence, source) VALUES
('BDO.*FEE', '6510', 'Bank Charges', 'bank_charge', 1.00, 'manual'),
('UNIONBANK.*FEE', '6510', 'Bank Charges', 'bank_charge', 1.00, 'manual'),
('BPI.*FEE', '6510', 'Bank Charges', 'bank_charge', 1.00, 'manual'),
('METROBANK.*FEE', '6510', 'Bank Charges', 'bank_charge', 1.00, 'manual'),
('GCASH.*FEE', '6510', 'Bank Charges', 'bank_charge', 1.00, 'manual'),
('PAYMAYA.*FEE', '6510', 'Bank Charges', 'bank_charge', 1.00, 'manual'),
('INSTAPAY.*FEE', '6510', 'Bank Charges', 'bank_charge', 1.00, 'manual'),
('PESONET.*FEE', '6510', 'Bank Charges', 'bank_charge', 1.00, 'manual'),
('ANNUAL FEE', '6510', 'Bank Charges', 'bank_charge', 1.00, 'manual'),
('FINANCE CHARGE', '6520', 'Interest Expense', 'bank_charge', 1.00, 'manual'),
('INTEREST CHARGE', '6520', 'Interest Expense', 'bank_charge', 1.00, 'manual'),
('LATE PAYMENT', '6521', 'Penalties & Fees', 'bank_charge', 1.00, 'manual')
ON CONFLICT (merchant_pattern) DO NOTHING;

-- -----------------------------------------------------------------------------
-- E-commerce & Retail
-- -----------------------------------------------------------------------------
INSERT INTO merchant_lookup (merchant_pattern, account_code, account_name, category, confidence, source) VALUES
('LAZADA', '6220', 'General Supplies', 'expense', 0.70, 'manual'),
('SHOPEE', '6220', 'General Supplies', 'expense', 0.70, 'manual'),
('ZALORA', '6220', 'General Supplies', 'expense', 0.70, 'manual'),
('SM STORE', '6220', 'General Supplies', 'expense', 0.70, 'manual'),
('ROBINSONS', '6220', 'General Supplies', 'expense', 0.70, 'manual'),
('PUREGOLD', '6220', 'General Supplies', 'expense', 0.70, 'manual'),
('S&R', '6220', 'General Supplies', 'expense', 0.70, 'manual'),
('LANDERS', '6220', 'General Supplies', 'expense', 0.70, 'manual')
ON CONFLICT (merchant_pattern) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Professional Services
-- -----------------------------------------------------------------------------
INSERT INTO merchant_lookup (merchant_pattern, account_code, account_name, category, confidence, source) VALUES
('SGV', '6610', 'Professional Fees - Audit', 'expense', 1.00, 'manual'),
('KPMG', '6610', 'Professional Fees - Audit', 'expense', 1.00, 'manual'),
('DELOITTE', '6610', 'Professional Fees - Audit', 'expense', 1.00, 'manual'),
('PWC', '6610', 'Professional Fees - Audit', 'expense', 1.00, 'manual'),
('PRICEWATERHOUSE', '6610', 'Professional Fees - Audit', 'expense', 1.00, 'manual'),
('LAW FIRM', '6620', 'Professional Fees - Legal', 'expense', 0.90, 'manual'),
('ATTORNEY', '6620', 'Professional Fees - Legal', 'expense', 0.90, 'manual'),
('NOTARY', '6620', 'Professional Fees - Legal', 'expense', 0.95, 'manual')
ON CONFLICT (merchant_pattern) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Insurance
-- -----------------------------------------------------------------------------
INSERT INTO merchant_lookup (merchant_pattern, account_code, account_name, category, confidence, source) VALUES
('SUNLIFE', '6710', 'Insurance', 'expense', 1.00, 'manual'),
('MANULIFE', '6710', 'Insurance', 'expense', 1.00, 'manual'),
('AXA', '6710', 'Insurance', 'expense', 1.00, 'manual'),
('PRUDENTIAL', '6710', 'Insurance', 'expense', 1.00, 'manual'),
('BPI-PHILAM', '6710', 'Insurance', 'expense', 1.00, 'manual'),
('PNBGEN', '6710', 'Insurance', 'expense', 1.00, 'manual'),
('MALAYAN', '6710', 'Insurance', 'expense', 1.00, 'manual'),
('PHILAM', '6710', 'Insurance', 'expense', 1.00, 'manual')
ON CONFLICT (merchant_pattern) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Government & Taxes
-- -----------------------------------------------------------------------------
INSERT INTO merchant_lookup (merchant_pattern, account_code, account_name, category, confidence, source) VALUES
('BIR', '6810', 'Taxes & Licenses', 'expense', 1.00, 'manual'),
('SSS', '6820', 'Government Contributions', 'expense', 1.00, 'manual'),
('PHILHEALTH', '6820', 'Government Contributions', 'expense', 1.00, 'manual'),
('PAG-IBIG', '6820', 'Government Contributions', 'expense', 1.00, 'manual'),
('HDMF', '6820', 'Government Contributions', 'expense', 1.00, 'manual'),
('SEC', '6810', 'Taxes & Licenses', 'expense', 1.00, 'manual'),
('DTI', '6810', 'Taxes & Licenses', 'expense', 1.00, 'manual'),
('LGU', '6810', 'Taxes & Licenses', 'expense', 0.90, 'manual'),
('BUSINESS PERMIT', '6810', 'Taxes & Licenses', 'expense', 1.00, 'manual')
ON CONFLICT (merchant_pattern) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Gaming Industry Specific (for Solaire, COD, etc.)
-- -----------------------------------------------------------------------------
INSERT INTO merchant_lookup (merchant_pattern, account_code, account_name, category, confidence, source) VALUES
('PAGCOR', '6910', 'Gaming Regulatory Fees', 'expense', 1.00, 'manual'),
('CASINO.*LICENSE', '6910', 'Gaming Regulatory Fees', 'expense', 0.95, 'manual'),
('JUNKET.*COMMISSION', '5100', 'Junket Commission Expense', 'commission', 1.00, 'manual'),
('ROLLING.*COMMISSION', '5100', 'Junket Commission Expense', 'commission', 1.00, 'manual'),
('VIP.*REBATE', '5100', 'Junket Commission Expense', 'commission', 0.95, 'manual')
ON CONFLICT (merchant_pattern) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Accommodation (for Tours entity)
-- -----------------------------------------------------------------------------
INSERT INTO merchant_lookup (merchant_pattern, account_code, account_name, category, confidence, source) VALUES
('HOTEL', '5200', 'Accommodation Costs', 'cos', 0.85, 'manual'),
('AIRBNB', '5200', 'Accommodation Costs', 'cos', 0.90, 'manual'),
('AGODA', '5200', 'Accommodation Costs', 'cos', 0.95, 'manual'),
('BOOKING.COM', '5200', 'Accommodation Costs', 'cos', 0.95, 'manual'),
('EXPEDIA', '5200', 'Accommodation Costs', 'cos', 0.95, 'manual')
ON CONFLICT (merchant_pattern) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Retail (for Midori no Mart)
-- -----------------------------------------------------------------------------
INSERT INTO merchant_lookup (merchant_pattern, account_code, account_name, category, confidence, source) VALUES
('WHOLESALE.*SUPPLIER', '5300', 'Cost of Goods Sold', 'cos', 0.90, 'manual'),
('DISTRIBUTOR', '5300', 'Cost of Goods Sold', 'cos', 0.85, 'manual'),
('INVENTORY.*PURCHASE', '5300', 'Cost of Goods Sold', 'cos', 0.95, 'manual')
ON CONFLICT (merchant_pattern) DO NOTHING;

-- =============================================================================
-- End of Seed Data
-- =============================================================================

-- Log seed completion
DO $$
BEGIN
    RAISE NOTICE 'Merchant seed data loaded: % rows', (SELECT COUNT(*) FROM merchant_lookup);
END $$;
