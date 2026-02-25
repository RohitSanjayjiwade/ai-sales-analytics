from django.db import models


class Product(models.Model):
    """Products available for sale."""

    class Category(models.TextChoices):
        ELECTRONICS = 'electronics', 'Electronics'
        CLOTHING = 'clothing', 'Clothing'
        FOOD = 'food', 'Food'
        OTHER = 'other', 'Other'

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=Category.choices, default=Category.OTHER)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sales_product'

    def __str__(self):
        return self.name


class Order(models.Model):
    """Customer purchase orders."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'

    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sales_order'

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"


class OrderItem(models.Model):
    """Individual line items inside an order."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'sales_order_item'

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"
