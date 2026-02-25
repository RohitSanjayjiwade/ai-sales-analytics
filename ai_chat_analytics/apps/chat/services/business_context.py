BUSINESS_CONTEXT = """
BUSINESS RULES:
- "Sales" and "revenue" always refer to total_amount, never quantity
- Cancelled and refunded orders must NEVER be included in sales/revenue figures
- "Active orders" means orders with status = 'pending' or 'completed'
- "Top products" means ORDER BY SUM(quantity) DESC or SUM(total_price) DESC
- All monetary values are in Indian Rupees (₹) — always use ₹ symbol, never $

TABLE RELATIONSHIPS:
- sales_order_item.order_id → sales_order.id
- sales_order_item.product_id → sales_product.id

COMMON PATTERNS:
- Total sales for a period: SELECT SUM(total_amount) FROM sales_order WHERE status='completed' AND <date condition>
- Order count: SELECT COUNT(*) FROM sales_order WHERE <conditions>
- Top products: SELECT p.name, SUM(oi.quantity) as units_sold FROM sales_order_item oi JOIN sales_product p ON oi.product_id = p.id GROUP BY p.id, p.name ORDER BY units_sold DESC LIMIT 10
- Sales by category: SELECT p.category, SUM(oi.total_price) as revenue FROM sales_order_item oi JOIN sales_product p ON oi.product_id = p.id JOIN sales_order o ON oi.order_id = o.id WHERE o.status='completed' GROUP BY p.category
"""
