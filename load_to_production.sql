
-- mapping_script.sql
-- Maps CSV data to production schema

-- 1. Create staging tables matching CSV structure
CREATE TEMP TABLE staging_clients (
    client_num TEXT,
    client_name TEXT
);

CREATE TEMP TABLE staging_sales (
    col0 TEXT,
    quantity TEXT,
    client_num TEXT,
    unit_price TEXT,
    col4 TEXT,
    col5 TEXT,
    col6 TEXT,
    sku TEXT,
    product_name TEXT,
    sale_date TEXT,
    col10 TEXT,
    col11 TEXT,
    col12 TEXT,
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
\copy staging_clients FROM 'output/data/clientes_15_al_24.csv' WITH CSV;
\copy staging_sales FROM 'output/data/venta_15_al_24.csv' WITH CSV;
\copy staging_returns FROM 'output/data/devolucion_15_al_24.csv' WITH CSV;

-- 3. Clean and insert clients
INSERT INTO clients (client_name)
SELECT DISTINCT trim(client_name)
FROM staging_clients
WHERE trim(client_name) != ''
  AND trim(client_name) NOT IN (SELECT client_name FROM clients)
ON CONFLICT DO NOTHING;

-- 4. Insert products from sales data
INSERT INTO products (sku, product_name, category, supply_type)
SELECT DISTINCT 
    trim(sku),
    trim(product_name),
    'General',  -- Default category
    'Regular'   -- Default supply type
FROM staging_sales
WHERE trim(sku) != ''
  AND trim(sku) NOT IN (SELECT sku FROM products)
ON CONFLICT (sku) DO NOTHING;

-- 5. Insert sales with proper FK mappings
INSERT INTO sales_partitioned (product_id, client_id, quantity, unit_price, sale_datetime)
SELECT 
    p.product_id,
    c.client_id,
    s.quantity::INTEGER,
    s.unit_price::NUMERIC,
    s.sale_date::TIMESTAMP WITH TIME ZONE
FROM staging_sales s
JOIN products p ON trim(p.sku) = trim(s.sku)
JOIN staging_clients sc ON trim(sc.client_num) = trim(s.client_num)
JOIN clients c ON trim(c.client_name) = trim(sc.client_name)
WHERE s.quantity ~ '^\d+$'  -- Only numeric quantities
  AND s.unit_price ~ '^\d+\.?\d*$'  -- Valid prices
  AND s.sale_date IS NOT NULL
  AND s.sale_date != '';

-- 6. Count results
SELECT 'Clients loaded:' as metric, COUNT(*) as count FROM clients;
SELECT 'Products loaded:' as metric, COUNT(*) as count FROM products;
SELECT 'Sales loaded:' as metric, COUNT(*) as count FROM sales_partitioned WHERE sale_datetime >= '2021-01-01';

-- 7. Drop temp tables
DROP TABLE staging_clients, staging_sales, staging_returns;
