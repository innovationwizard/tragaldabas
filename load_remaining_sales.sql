-- Efficiently load remaining sales by creating a simple client mapping
-- This approach creates one client per unique client number in sales data

-- 1. Create staging table for sales only
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

-- 2. Load sales data
\copy staging_sales FROM '/Users/jorgeluiscontrerasherrera/Documents/_git/tragaldabas/output/data/venta_15_al_24.csv' WITH CSV HEADER;

-- 3. Create clients for all unique client numbers in sales data
INSERT INTO clients (client_name)
SELECT DISTINCT 'Client_' || trim(client_num) as client_name
FROM staging_sales
WHERE trim(client_num) != ''
  AND trim(client_num) IS NOT NULL
  AND 'Client_' || trim(client_num) NOT IN (SELECT client_name FROM clients WHERE is_deleted = false);

-- 4. Insert sales in batches (this will be much faster)
INSERT INTO sales_partitioned (product_id, client_id, quantity, unit_price, sale_datetime)
SELECT 
    p.product_id,
    c.client_id,
    s.quantity::NUMERIC::INTEGER,
    s.unit_price::NUMERIC,
    s.sale_date::TIMESTAMP WITH TIME ZONE
FROM staging_sales s
JOIN products p ON trim(p.product_name) = trim(s.product_name) AND p.is_deleted = false
JOIN clients c ON trim(c.client_name) = 'Client_' || trim(s.client_num) AND c.is_deleted = false
WHERE s.quantity ~ '^\d+\.?\d*$'
  AND s.unit_price ~ '^\d+\.?\d*$'
  AND s.sale_date IS NOT NULL
  AND s.sale_date != ''
  AND s.product_name IS NOT NULL
  AND s.product_name != '';

-- 5. Show final results
SELECT 'Total Sales Loaded:' as metric, COUNT(*) as count FROM sales_partitioned WHERE is_deleted = false;
SELECT 'Total Clients:' as metric, COUNT(*) as count FROM clients WHERE is_deleted = false;
SELECT 'Total Products:' as metric, COUNT(*) as count FROM products WHERE is_deleted = false;

-- 6. Show sales by product
SELECT p.sku, p.product_name, COUNT(s.sale_id) as sales_count 
FROM products p 
LEFT JOIN sales_partitioned s ON p.product_id = s.product_id AND s.is_deleted = false
WHERE p.is_deleted = false
GROUP BY p.sku, p.product_name
ORDER BY sales_count DESC;

-- 7. Clean up
DROP TABLE staging_sales;
