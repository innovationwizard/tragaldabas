-- mapping_script.sql
-- Maps CSV data to production schema

-- 1. Create staging tables matching CSV structure
CREATE TEMP TABLE staging_clients (
    col0 TEXT,
    client_name TEXT,
    col2 TEXT,
    col3 TEXT
);

CREATE TEMP TABLE staging_sales (
    col0 TEXT,
    quantity TEXT,
    client_num TEXT,
    unit_price TEXT,
    col4 TEXT,
    col5 TEXT,
    col6 TEXT,
    col7 TEXT,
    product_name TEXT,
    sale_date TEXT,
    col10 TEXT,
    col11 TEXT,
    sku TEXT,
    col13 TEXT,
    col14 TEXT,
    col15 TEXT,
    col16 TEXT,
    col17 TEXT,
    col18 TEXT
);

CREATE TEMP TABLE staging_returns (
    col0 TEXT,
    quantity TEXT,
    col2 TEXT,
    col3 TEXT,
    sku TEXT,
    product_name TEXT,
    return_date TEXT,
    col7 TEXT,
    col8 TEXT,
    col9 TEXT,
    col10 TEXT,
    col11 TEXT,
    col12 TEXT
);

-- 2. Load CSV data
\copy staging_clients FROM '/Users/jorgeluiscontrerasherrera/Documents/_git/tragaldabas/output/data/clientes_15_al_24.csv' WITH CSV HEADER;
\copy staging_sales FROM '/Users/jorgeluiscontrerasherrera/Documents/_git/tragaldabas/output/data/venta_15_al_24.csv' WITH CSV HEADER;
\copy staging_returns FROM '/Users/jorgeluiscontrerasherrera/Documents/_git/tragaldabas/output/data/devolucion_15_al_24.csv' WITH CSV HEADER;

-- 3. Clean and insert clients
INSERT INTO clients (client_name)
SELECT DISTINCT trim(client_name)
FROM staging_clients
WHERE trim(client_name) != ''
  AND trim(client_name) IS NOT NULL
  AND trim(client_name) NOT IN (SELECT client_name FROM clients WHERE is_deleted = false)
ON CONFLICT DO NOTHING;

-- 4. Insert products from sales data
INSERT INTO products (sku, product_name, category)
SELECT DISTINCT 
    trim(sku),
    trim(product_name),
    'General'  -- Default category
FROM staging_sales
WHERE trim(sku) != ''
  AND trim(sku) IS NOT NULL
  AND trim(sku) NOT IN (SELECT sku FROM products WHERE sku IS NOT NULL AND is_deleted = false)
ON CONFLICT DO NOTHING;

-- 5. Insert sales with proper FK mappings
INSERT INTO sales_partitioned (product_id, client_id, quantity, unit_price, sale_datetime)
SELECT 
    p.product_id,
    c.client_id,
    s.quantity::NUMERIC::INTEGER,
    s.unit_price::NUMERIC,
    s.sale_date::TIMESTAMP WITH TIME ZONE
FROM staging_sales s
JOIN products p ON trim(p.sku) = trim(s.sku) AND p.is_deleted = false
JOIN staging_clients sc ON trim(sc.col0) = trim(s.client_num)
JOIN clients c ON trim(c.client_name) = trim(sc.client_name) AND c.is_deleted = false
WHERE s.quantity ~ '^\d+\.?\d*$'  -- Only numeric quantities (allowing decimals)
  AND s.unit_price ~ '^\d+\.?\d*$'  -- Valid prices
  AND s.sale_date IS NOT NULL
  AND s.sale_date != ''
  AND s.sku IS NOT NULL
  AND s.sku != '';

-- 6. Count results
SELECT 'Clients loaded:' as metric, COUNT(*) as count FROM clients WHERE is_deleted = false;
SELECT 'Products loaded:' as metric, COUNT(*) as count FROM products WHERE is_deleted = false;
SELECT 'Sales loaded:' as metric, COUNT(*) as count FROM sales_partitioned WHERE sale_datetime >= '2021-01-01' AND is_deleted = false;

-- 7. Drop temp tables
DROP TABLE staging_clients, staging_sales, staging_returns;

