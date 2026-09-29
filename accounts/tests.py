from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Category, Offer, Product, ProductVariant


class AdminDashboardChartTests(TestCase):

	def setUp(self):
		self.admin = get_user_model().objects.create_superuser(
			username='chart-admin',
			email='chart-admin@example.com',
			password='test-password'
		)
		self.client.force_login(self.admin)

	def test_dashboard_charts_use_monthly_order_and_status_data(self):
		shared_fields = {
			'user': self.admin,
			'full_name': 'Chart Customer',
			'phone': '5551234567',
			'address': '1 Chart Street',
			'city': 'Chart City',
			'state': 'Chart State',
			'pincode': '12345',
		}
		Order.objects.create(
			**shared_fields,
			total_amount=Decimal('125.00'),
			status='Pending'
		)
		Order.objects.create(
			**shared_fields,
			total_amount=Decimal('325.00'),
			status='Delivered'
		)

		response = self.client.get(reverse('admin_dashboard'))

		self.assertEqual(response.status_code, 200)
		monthly_data = response.context['monthly_chart_data']
		self.assertEqual(monthly_data['orders'][-1], 2)
		self.assertEqual(monthly_data['revenue'][-1], 450.0)
		self.assertEqual(
			response.context['status_chart_data']['values'],
			[1, 0, 0, 1, 0]
		)
		self.assertContains(response, 'monthlyOrdersChart')
		self.assertContains(response, 'orderStatusChart')
		self.assertContains(response, 'admin-table-search')
		self.assertContains(response, 'admin-table-sort')
		self.assertContains(response, 'admin-table-low-stock')
		self.assertEqual(response.content.count(b'<table'), 1)
		self.assertNotContains(response, 'Overview data')

	def test_inventory_dashboard_reports_units_and_restock_adds_quantity(self):
		category = Category.objects.create(name='Inventory Clothing')
		product = Product.objects.create(
			name='Inventory Shirt',
			category=category,
			description='Test product'
		)
		variant = ProductVariant.objects.create(
			product=product,
			size='M',
			price=Decimal('100.00'),
			stock=2
		)
		Offer.objects.create(
			variant=variant,
			offer_price=Decimal('80.00'),
			start_date=timezone.now() - timedelta(minutes=1),
			end_date=timezone.now() + timedelta(days=1)
		)
		base_order_fields = {
			'user': self.admin,
			'full_name': 'Inventory Customer',
			'phone': '5551234567',
			'address': '1 Inventory Street',
			'city': 'Inventory City',
			'state': 'Inventory State',
			'pincode': '12345',
			'total_amount': Decimal('100.00'),
		}
		delivered_order = Order.objects.create(
			**base_order_fields,
			status='Delivered'
		)
		pending_order = Order.objects.create(
			**base_order_fields,
			status='Pending'
		)
		OrderItem.objects.create(
			order=delivered_order,
			product=product,
			variant=variant,
			quantity=2,
			price=Decimal('100.00'),
			stock_reserved=True
		)
		OrderItem.objects.create(
			order=pending_order,
			product=product,
			variant=variant,
			quantity=3,
			price=Decimal('100.00'),
			stock_reserved=True
		)

		response = self.client.get(reverse('admin_dashboard'))
		inventory_variant = next(
			item for item in response.context['inventory_variants']
			if item.pk == variant.pk
		)
		self.assertEqual(inventory_variant.sold_quantity, 2)
		self.assertEqual(inventory_variant.pending_quantity, 3)
		self.assertTrue(inventory_variant.is_low_stock)
		self.assertEqual(inventory_variant.dashboard_offer.offer_price, Decimal('80.00'))
		self.assertContains(response, 'Restore stock')
		self.assertContains(response, '₹80.00')

		low_stock_response = self.client.get(
			reverse('admin_dashboard'),
			{'low_stock': '1', 'per_page': 10, 'page': 1}
		)
		self.assertEqual(low_stock_response.status_code, 200)
		self.assertEqual(low_stock_response.context['inventory_summary']['low_stock_variants'], 1)
		self.assertContains(low_stock_response, 'name="low_stock" value="1" checked')

		response = self.client.post(
			reverse('restock_variant', args=[variant.pk]),
			{'quantity': 4}
		)
		self.assertEqual(response.status_code, 302)
		variant.refresh_from_db()
		self.assertEqual(variant.stock, 6)


class AdminPriceHistoryTests(TestCase):

	def setUp(self):
		admin = get_user_model().objects.create_superuser(
			username='price-history-admin',
			email='price-history-admin@example.com',
			password='test-password'
		)
		self.client.force_login(admin)

	def test_price_history_page_keeps_non_offer_price_events_in_order(self):
		category = Category.objects.create(name='Price History Clothing')
		product = Product.objects.create(
			name='Price History Shirt',
			category=category,
			description='Test product'
		)
		variant = ProductVariant.objects.create(
			product=product,
			price=Decimal('100.00')
		)
		variant.price = Decimal('120.00')
		variant.save()

		response = self.client.get(reverse('admin_price_history'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(
			[entry.price_type for entry in response.context['price_history']],
			['original', 'updated']
		)
		self.assertContains(response, 'Regular product price changes')
		self.assertContains(response, 'admin-table-search')
		self.assertContains(response, 'admin-table-sort')
		self.assertContains(response, 'admin-table-pagination')
		self.assertEqual(response.content.count(b'<table'), 1)

	def test_offer_product_history_is_shown_in_offers_not_regular_price_history(self):
		category = Category.objects.create(name='Offer History Clothing')
		product = Product.objects.create(
			name='Offer History Shirt',
			category=category,
			description='Test product'
		)
		variant = ProductVariant.objects.create(
			product=product,
			price=Decimal('100.00')
		)
		offer = Offer.objects.create(
			variant=variant,
			offer_price=Decimal('80.00'),
			start_date=timezone.now() - timedelta(minutes=1),
			end_date=timezone.now() + timedelta(days=1)
		)

		price_response = self.client.get(reverse('admin_price_history'))
		self.assertNotContains(price_response, 'Offer History Shirt')

		offer_response = self.client.get(reverse('admin_offers'))
		self.assertContains(offer_response, 'Offer History Shirt')
		self.assertContains(offer_response, 'Price after offer')
		self.assertContains(offer_response, 'Price before offer')
		self.assertContains(offer_response, '₹100.00')
		self.assertContains(offer_response, '₹100.00')


class AdminOffersTableTests(TestCase):

	def test_offer_created_timestamp_is_rendered(self):
		admin = get_user_model().objects.create_superuser(
			username='offers-table-admin',
			email='offers-table-admin@example.com',
			password='test-password'
		)
		category = Category.objects.create(name='Offers Table Clothing')
		product = Product.objects.create(
			name='Offers Table Shirt',
			category=category,
			description='Test product'
		)
		variant = ProductVariant.objects.create(
			product=product,
			price=Decimal('100.00')
		)
		offer = Offer.objects.create(
			variant=variant,
			offer_price=Decimal('80.00'),
			start_date=timezone.now() - timedelta(minutes=1),
			end_date=timezone.now() + timedelta(days=1)
		)
		self.client.force_login(admin)

		response = self.client.get(reverse('admin_offers'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Created')
		self.assertContains(response, 'admin-searchable-table')
		created_at_label = timezone.localtime(offer.created_at).strftime('%d %b %Y, %I:%M %p')
		self.assertContains(response, created_at_label)


class AdminCategoryHierarchyTests(TestCase):

	def test_categories_table_reports_parent_collection_and_product_counts(self):
		admin = get_user_model().objects.create_superuser(
			username='category-table-admin',
			email='category-table-admin@example.com',
			password='test-password'
		)
		parent = Category.objects.create(name='Table Sarees')
		collection = Category.objects.create(name='Table Silk', parent=parent)
		product = Product.objects.create(
			name='Table Silk Saree',
			category=collection,
			description='Test product'
		)
		self.client.force_login(admin)

		response = self.client.get(reverse('admin_categories'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'main categories')
		self.assertContains(response, 'Collections')
		self.assertContains(response, 'Parent category')
		self.assertContains(response, 'Table Sarees')
		self.assertContains(response, 'Table Silk')
		self.assertTrue(any(item.pk == parent.pk and item.collection_count == 1 for item in response.context['categories']))
		self.assertTrue(any(item.pk == collection.pk and item.product_count == 1 for item in response.context['categories']))


class AdminSearchableTablesTests(TestCase):

	def test_admin_list_pages_use_shared_searchable_table_controls(self):
		admin = get_user_model().objects.create_superuser(
			username='admin-table-controls',
			email='admin-table-controls@example.com',
			password='test-password'
		)
		category = Category.objects.create(name='Admin Table Clothing')
		product = Product.objects.create(
			name='Admin Table Product',
			category=category,
			description='Test product'
		)
		variant = ProductVariant.objects.create(
			product=product,
			price=Decimal('100.00')
		)
		Offer.objects.create(
			variant=variant,
			offer_price=Decimal('80.00'),
			start_date=timezone.now() - timedelta(minutes=1),
			end_date=timezone.now() + timedelta(days=1)
		)
		self.client.force_login(admin)

		for route_name in (
			'admin_products',
			'admin_categories',
			'admin_orders',
			'admin_users',
			'admin_offers',
		):
			with self.subTest(route=route_name):
				response = self.client.get(reverse(route_name))
				self.assertEqual(response.status_code, 200)
				self.assertContains(response, 'admin-searchable-table')

	def test_product_list_uses_django_paginator_and_preserves_table_filters(self):
		admin = get_user_model().objects.create_superuser(
			username='admin-paginator-test',
			email='admin-paginator-test@example.com',
			password='test-password'
		)
		category = Category.objects.create(name='Paginator Clothing')
		for index in range(12):
			Product.objects.create(
				name=f'Paginator Product {index:02d}',
				category=category,
				description='Test product'
			)
		self.client.force_login(admin)

		response = self.client.get(
			reverse('admin_products'),
			{
				'q': 'Paginator Product',
				'sort': 'name',
				'direction': 'desc',
				'per_page': 10,
				'page': 2,
			}
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['products'].paginator.count, 12)
		self.assertEqual(response.context['products'].number, 2)
		self.assertEqual(len(response.context['products']), 2)
		self.assertEqual(
			[product.name for product in response.context['products']],
			['Paginator Product 01', 'Paginator Product 00']
		)
		self.assertContains(response, 'page=1')
		self.assertEqual(response.context['table_search'], 'Paginator Product')
