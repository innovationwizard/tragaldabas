-- Final corrected mapping script for production schema
-- Loads the 5 products with correct SKUs and maps sales by exact product name matching

-- 1. Create staging tables
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

-- 2. Load CSV data
\copy staging_clients FROM '/Users/jorgeluiscontrerasherrera/Documents/_git/tragaldabas/output/data/clientes_15_al_24.csv' WITH CSV HEADER;
\copy staging_sales FROM '/Users/jorgeluiscontrerasherrera/Documents/_git/tragaldabas/output/data/venta_15_al_24.csv' WITH CSV HEADER;

-- 3. Insert the 5 products with correct SKUs and exact names
INSERT INTO products (sku, product_name, category, cost)
VALUES 
    ('77205001', 'BANDEJA 2P TERMO FOM BIO 10/50', 'DUROPORT', 47.241151),
    ('77205207', 'VASO No 8 OZ VIVA DUROPORT BIODEG. 40X25', 'DUROPORT', 115.469956),
    ('77201046', 'VASO DUROPORT No. 10 REYMA 40-25', 'DUROPORT', 151.205293),
    ('77201000', 'VASO DUROPORT No. 8 REYMA 40-25', 'DUROPORT', 126.215369),
    ('77201041', 'ENVASE DUROPORT REYMA 16 ONZ. 20/25', 'DUROPORT', 134.206436);

-- 4. Clean and insert clients (skip if already loaded)
INSERT INTO clients (client_name)
SELECT DISTINCT trim(client_name)
FROM staging_clients
WHERE trim(client_name) != ''
  AND trim(client_name) IS NOT NULL
  AND trim(client_name) NOT IN (SELECT client_name FROM clients WHERE is_deleted = false)
ON CONFLICT DO NOTHING;

-- 5. Insert sales with exact product name matching
INSERT INTO sales_partitioned (product_id, client_id, quantity, unit_price, sale_datetime)
SELECT 
    p.product_id,
    c.client_id,
    s.quantity::NUMERIC::INTEGER,
    s.unit_price::NUMERIC,
    s.sale_date::TIMESTAMP WITH TIME ZONE
FROM staging_sales s
JOIN products p ON trim(p.product_name) = trim(s.product_name) AND p.is_deleted = false
JOIN staging_clients sc ON trim(sc.col0) = trim(s.client_num)
JOIN clients c ON trim(c.client_name) = trim(sc.client_name) AND c.is_deleted = false
WHERE s.quantity ~ '^\d+\.?\d*$'  -- Only numeric quantities
  AND s.unit_price ~ '^\d+\.?\d*$'  -- Valid prices
  AND s.sale_date IS NOT NULL
  AND s.sale_date != ''
  AND s.product_name IS NOT NULL
  AND s.product_name != '';

-- 6. Count results
SELECT 'Clients loaded:' as metric, COUNT(*) as count FROM clients WHERE is_deleted = false;
SELECT 'Products loaded:' as metric, COUNT(*) as count FROM products WHERE is_deleted = false;
SELECT 'Sales loaded:' as metric, COUNT(*) as count FROM sales_partitioned WHERE sale_datetime >= '2021-01-01' AND is_deleted = false;

-- 7. Show product mapping with sales counts
SELECT p.sku, p.product_name, COUNT(s.sale_id) as sales_count 
FROM products p 
LEFT JOIN sales_partitioned s ON p.product_id = s.product_id AND s.is_deleted = false
WHERE p.is_deleted = false
GROUP BY p.sku, p.product_name
ORDER BY p.sku;

-- 8. Drop temp tables
DROP TABLE staging_clients, staging_sales;
