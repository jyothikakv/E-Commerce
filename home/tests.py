from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from products.models import Category, Offer, Product, ProductVariant


class HomeOfferExpiryTests(TestCase):

	def setUp(self):
		category = Category.objects.create(name='Offer Test')
		product = Product.objects.create(
			name='Offer Test Dress',
			category=category,
			description='Test offer expiry'
		)
		self.variant = ProductVariant.objects.create(
			product=product,
			price=Decimal('250.00'),
			stock=5
		)

	def test_expired_offer_shows_current_original_price(self):
		current_time = timezone.now()
		Offer.objects.create(
			variant=self.variant,
			offer_price=Decimal('199.00'),
			start_date=current_time - timedelta(days=3),
			end_date=current_time - timedelta(seconds=1)
		)

		response = self.client.get('/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'OFFER ENDED')
		self.assertContains(response, '₹250.00')
		self.assertNotContains(response, '₹199.00')

	def test_active_offer_keeps_discount_price_visible(self):
		current_time = timezone.now()
		Offer.objects.create(
			variant=self.variant,
			offer_price=Decimal('199.00'),
			start_date=current_time - timedelta(seconds=1),
			end_date=current_time + timedelta(days=3)
		)

		response = self.client.get('/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, '₹199.00')
		self.assertNotContains(response, 'OFFER ENDED')
