from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Category, Offer, PriceHistory, Product, ProductVariant


class PriceHistoryTests(TestCase):
	def setUp(self):
		category = Category.objects.create(name='Clothing')
		product = Product.objects.create(
			name='T-shirt',
			category=category,
			description='Cotton T-shirt'
		)
		self.variant = ProductVariant.objects.create(
			product=product,
			price=Decimal('100.00')
		)

	def test_variant_price_changes_are_recorded(self):
		original = self.variant.price_history.get()
		self.assertEqual(original.price_type, 'original')
		self.assertEqual(original.price, Decimal('100.00'))
		self.assertIsNone(original.end_date)

		self.variant.price = Decimal('120.00')
		self.variant.save()

		original.refresh_from_db()
		updated = self.variant.price_history.get(price_type='updated')
		self.assertIsNotNone(original.end_date)
		self.assertEqual(updated.price, Decimal('120.00'))

	def test_offer_price_is_recorded(self):
		start_date = timezone.now()
		end_date = start_date + timedelta(days=7)

		Offer.objects.create(
			variant=self.variant,
			offer_price=Decimal('80.00'),
			start_date=start_date,
			end_date=end_date
		)

		offer_history = self.variant.price_history.get(price_type='offer')
		self.assertEqual(offer_history.price, Decimal('80.00'))
		self.assertEqual(offer_history.start_date, start_date)
		self.assertEqual(offer_history.end_date, end_date)

	def test_offer_records_restored_price_after_ending(self):
		start_date = timezone.now()
		end_date = start_date + timedelta(days=7)
		original_history = self.variant.price_history.get(price_type='original')

		Offer.objects.create(
			variant=self.variant,
			offer_price=Decimal('80.00'),
			start_date=start_date,
			end_date=end_date
		)

		original_history.refresh_from_db()
		offer_history = self.variant.price_history.get(price_type='offer')
		restored_history = self.variant.price_history.get(price_type='after_offer')

		self.assertEqual(original_history.end_date, start_date)
		self.assertEqual(offer_history.price, Decimal('80.00'))
		self.assertEqual(restored_history.price, Decimal('100.00'))
		self.assertEqual(restored_history.start_date, end_date)

	def test_base_price_change_updates_scheduled_restored_price(self):
		start_date = timezone.now() - timedelta(minutes=1)
		end_date = timezone.now() + timedelta(days=7)
		Offer.objects.create(
			variant=self.variant,
			offer_price=Decimal('80.00'),
			start_date=start_date,
			end_date=end_date
		)

		self.variant.price = Decimal('120.00')
		self.variant.save()

		restored_history = self.variant.price_history.get(price_type='after_offer')
		self.assertEqual(restored_history.price, Decimal('120.00'))


class ProductSlugTests(TestCase):
	def setUp(self):
		self.category = Category.objects.create(name='Clothing')

	def make_product(self, name):
		return Product.objects.create(
			name=name,
			category=self.category,
			description='Test product'
		)

	def test_product_slug_is_generated_from_name(self):
		product = self.make_product('Blue Cotton Shirt')

		self.assertEqual(product.slug, 'blue-cotton-shirt')

	def test_duplicate_product_names_get_unique_slugs(self):
		first_product = self.make_product('Blue Cotton Shirt')
		second_product = self.make_product('Blue Cotton Shirt')

		self.assertEqual(first_product.slug, 'blue-cotton-shirt')
		self.assertEqual(second_product.slug, 'blue-cotton-shirt-2')


class ProductListSizeTests(TestCase):
	def setUp(self):
		self.category = Category.objects.create(name='Anarkali')
		self.product = Product.objects.create(
			name='Blue Anarkali',
			category=self.category,
			description='Test product'
		)
		ProductVariant.objects.create(
			product=self.product,
			size='S, M, L, XL, XXL',
			price=Decimal('100.00'),
			stock=5
		)

	@override_settings(ALLOWED_HOSTS=['testserver'])
	def test_size_filter_matches_complete_size_token(self):
		response = self.client.get('/products/?size=L')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(list(response.context['products']), [self.product])

	@override_settings(ALLOWED_HOSTS=['testserver'])
	def test_category_size_filter_uses_actual_available_sizes(self):
		response = self.client.get('/products/?category=Anarkali')

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context['has_sized_products'])
		self.assertEqual(
			response.context['available_sizes'],
			['S', 'M', 'L', 'XL', 'XXL']
		)
		self.assertContains(response, 'Filter size')
		self.assertNotContains(response, 'Size chart')
		self.assertNotContains(response, 'Sort size')

	@override_settings(ALLOWED_HOSTS=['testserver'])
	def test_category_filter_accepts_name_without_spaces(self):
		party_category = Category.objects.create(name='Party Wear')
		self.product.category = party_category
		self.product.save()

		response = self.client.get('/products/?category=Partywear')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['category_display_name'], 'Party Wear')
		self.assertEqual(list(response.context['products']), [self.product])
