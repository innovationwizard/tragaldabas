-- Final mapping script for production schema
-- Loads the 5 products from master file and maps sales by product name

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

CREATE TEMP TABLE staging_products (
    sku TEXT,
    nombre TEXT,
    descripcion TEXT,
    unidades_medida TEXT,
    categoria TEXT,
    tipo_abastecimiento TEXT,
    costo TEXT,
    precio_venta_mas_bajo TEXT,
    vida_util TEXT,
    cantidad_minima_pedido TEXT
);

-- 2. Load CSV data
\copy staging_clients FROM '/Users/jorgeluiscontrerasherrera/Documents/_git/tragaldabas/output/data/clientes_15_al_24.csv' WITH CSV HEADER;
\copy staging_sales FROM '/Users/jorgeluiscontrerasherrera/Documents/_git/tragaldabas/output/data/venta_15_al_24.csv' WITH CSV HEADER;
\copy staging_products FROM '/Users/jorgeluiscontrerasherrera/Documents/_git/tragaldabas/output/data/envio_de_datos_a_condor_datos maestro de producto.csv' WITH CSV HEADER;

-- 3. Insert the 5 products with correct SKUs
INSERT INTO products (sku, product_name, category, cost)
VALUES 
    ('77205001', 'BANDEJA', 'DUROPORT', 47.241151),
    ('77205207', 'VASO', 'DUROPORT', 115.469956),
    ('77201046', 'VASO', 'DUROPORT', 151.205293),
    ('77201000', 'VASO', 'DUROPORT', 126.215369),
    ('77201041', 'ENVASE', 'DUROPORT', 134.206436)
ON CONFLICT (sku) DO NOTHING;

-- 4. Clean and insert clients (skip if already loaded)
INSERT INTO clients (client_name)
SELECT DISTINCT trim(client_name)
FROM staging_clients
WHERE trim(client_name) != ''
  AND trim(client_name) IS NOT NULL
  AND trim(client_name) NOT IN (SELECT client_name FROM clients WHERE is_deleted = false)
ON CONFLICT DO NOTHING;

-- 5. Insert sales with proper FK mappings using product name matching
INSERT INTO sales_partitioned (product_id, client_id, quantity, unit_price, sale_datetime)
SELECT 
    p.product_id,
    c.client_id,
    s.quantity::NUMERIC::INTEGER,
    s.unit_price::NUMERIC,
    s.sale_date::TIMESTAMP WITH TIME ZONE
FROM staging_sales s
JOIN products p ON (
    (trim(s.product_name) LIKE '%BANDEJA%' AND p.sku = '77205001') OR
    (trim(s.product_name) LIKE '%VASO No.8 OZ VIVA DUROPORT%' AND p.sku = '77205207') OR
    (trim(s.product_name) LIKE '%VASO DUROPORT No. 10 REYMA%' AND p.sku = '77201046') OR
    (trim(s.product_name) LIKE '%VASO DUROPORT No. 8 REYMA%' AND p.sku = '77201000') OR
    (trim(s.product_name) LIKE '%ENVASE DUROPORT REYMA 16 ONZ%' AND p.sku = '77201041')
) AND p.is_deleted = false
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

-- 7. Show product mapping
SELECT p.sku, p.product_name, COUNT(s.sale_id) as sales_count 
FROM products p 
LEFT JOIN sales_partitioned s ON p.product_id = s.product_id AND s.is_deleted = false
WHERE p.is_deleted = false
GROUP BY p.sku, p.product_name
ORDER BY p.sku;

-- 8. Drop temp tables
DROP TABLE staging_clients, staging_sales, staging_products;
