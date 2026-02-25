import random
from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.sales.models import Product, Order, OrderItem


PRODUCTS = [
    ('iPhone 15', 'electronics', '999.99'),
    ('Samsung TV 55"', 'electronics', '799.99'),
    ('Nike Air Max', 'clothing', '129.99'),
    ('Levi Jeans', 'clothing', '59.99'),
    ('Laptop Dell XPS', 'electronics', '1299.99'),
    ('Coffee Maker', 'other', '49.99'),
    ('Organic Milk 1L', 'food', '3.99'),
    ('Bread Loaf', 'food', '2.49'),
    ('Wireless Headphones', 'electronics', '199.99'),
    ('T-Shirt Pack', 'clothing', '29.99'),
]

CUSTOMERS = [
    ('Alice Johnson', 'alice@example.com'),
    ('Bob Smith', 'bob@example.com'),
    ('Carol White', 'carol@example.com'),
    ('David Brown', 'david@example.com'),
    ('Eva Davis', 'eva@example.com'),
    ('Frank Miller', 'frank@example.com'),
    ('Grace Wilson', 'grace@example.com'),
    ('Henry Moore', 'henry@example.com'),
]


class Command(BaseCommand):
    help = 'Seed sample sales data for testing AI chat analytics'

    def add_arguments(self, parser):
        parser.add_argument('--orders', type=int, default=50, help='Number of orders to create')
        parser.add_argument('--clear', action='store_true', help='Clear existing data first')

    def handle(self, *args, **options):
        if options['clear']:
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Product.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing data.'))

        # Create products
        products = []
        for name, category, price in PRODUCTS:
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={'category': category, 'price': Decimal(price)}
            )
            products.append(product)
        self.stdout.write(f'Products ready: {len(products)}')

        # Create orders spread across last 30 days
        statuses = ['completed', 'completed', 'completed', 'pending', 'cancelled']
        order_count = options['orders']

        for i in range(order_count):
            customer = random.choice(CUSTOMERS)
            days_ago = random.randint(0, 30)
            order_date = timezone.now() - timedelta(days=days_ago)
            status = random.choice(statuses)

            order = Order.objects.create(
                customer_name=customer[0],
                customer_email=customer[1],
                status=status,
                created_at=order_date,
            )

            # Add 1-4 items per order
            total = Decimal('0')
            for _ in range(random.randint(1, 4)):
                product = random.choice(products)
                qty = random.randint(1, 3)
                unit_price = product.price
                total_price = unit_price * qty
                total += total_price
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=qty,
                    unit_price=unit_price,
                    total_price=total_price,
                )

            order.total_amount = total
            order.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully created {order_count} orders with items.'))
