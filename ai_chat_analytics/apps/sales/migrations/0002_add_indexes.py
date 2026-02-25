from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add indexes on the columns that the AI queries most:
      - sales_order.status         (WHERE status IN (...))
      - sales_order.created_at     (WHERE DATE(created_at) = ...)
      - sales_order.(status, created_at)  composite — covers both filters at once
      - sales_order_item.order_id  (JOIN sales_order ON order_id)
      - sales_order_item.product_id(JOIN sales_product ON product_id)
      - sales_product.category     (WHERE category = ...)
      - sales_product.is_active    (WHERE is_active = 1)
    """

    dependencies = [
        ('sales', '0001_initial'),
    ]

    operations = [
        # sales_order — single-column indexes
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status'], name='sales_order_status_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['created_at'], name='sales_order_created_at_idx'),
        ),
        # sales_order — composite index for "WHERE status=X AND date(created_at)=Y"
        migrations.AddIndex(
            model_name='order',
            index=models.Index(
                fields=['status', 'created_at'],
                name='sales_order_status_created_idx',
            ),
        ),
        # sales_order_item — FK join indexes
        migrations.AddIndex(
            model_name='orderitem',
            index=models.Index(fields=['order'], name='sales_orderitem_order_idx'),
        ),
        migrations.AddIndex(
            model_name='orderitem',
            index=models.Index(fields=['product'], name='sales_orderitem_product_idx'),
        ),
        # sales_product
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category'], name='sales_product_category_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['is_active'], name='sales_product_active_idx'),
        ),
    ]
