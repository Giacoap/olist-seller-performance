# olist-seller-performance

## Goal
Identify which Olist sellers deliver superior customer outcomes — measured by review score and delivery reliability — and what operational factors differentiate top performers from underperformers. Designed as a monitoring tool for the Seller Success team.

## Authoritative scope
La fuente de verdad para qué hace este análisis es `00_scoping.md`.
Si hay conflicto entre cualquier instrucción ad-hoc y ese documento, prevalece el documento.
Antes de modificar `00_scoping.md`, preguntar.

## Dataset
- **Fuente:** https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- **Período:** septiembre 2016 – octubre 2018
- **Tablas (en `data/`):**
  - `olist_orders_dataset.csv` — órdenes (status, timestamps de delivery)
  - `olist_order_items_dataset.csv` — items por orden, precio, freight, seller_id
  - `olist_order_payments_dataset.csv` — método de pago, cuotas
  - `olist_order_reviews_dataset.csv` — review_score (1–5) y comentarios
  - `olist_customers_dataset.csv` — customer_id, ciudad, estado
  - `olist_sellers_dataset.csv` — seller_id, ciudad, estado
  - `olist_products_dataset.csv` — categoría, dimensiones
  - `olist_geolocation_dataset.csv` — coordenadas por zip
  - `product_category_name_translation.csv` — categorías traducidas al inglés
- **Joins clave:** `order_id`, `seller_id`, `product_id`, `customer_id`, `product_category_name`

## Stack específico
- pandas, numpy
- matplotlib, seaborn (visualizaciones exploratorias)
- Tableau Public (dashboard final, fuera del script)

## Notas del dataset
- Filtrar `order_status = 'delivered'` para el análisis core (96.478 de 99.441 órdenes)
- Fechas en formato ISO, parsear con `pd.to_datetime`
- Encoding UTF-8
- `geolocation` tiene múltiples entradas por zip — agregar a nivel estado (no zip) para evitar ruido
- Sellers con menos de 5 órdenes entregadas se excluyen del tier segmentation (ver Métrica 1 en 00_scoping.md)
- Identidades de sellers anonimizadas (nombres de Game of Thrones)
