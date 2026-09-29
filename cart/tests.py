from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal

from cart.models import Cart, CartItem
from products.models import Category, Product, ProductVariant


class AddToCartTests(TestCase):
	def setUp(self):
		category = Category.objects.create(name='Clothing')
		self.product = Product.objects.create(
			name='Test Shirt',
			category=category,
			description='Test product'
		)
		self.variant = ProductVariant.objects.create(
			product=self.product,
			size='S, M, L',
			price=Decimal('100.00'),
			stock=4
		)

	def add_item(self, selected_size='M'):
		return self.client.post(
			f'/cart/add/{self.product.id}/',
			{
				'variant': self.variant.id,
				'selected_size': selected_size,
				'purchase_action': 'add_to_cart',
			},
			HTTP_X_REQUESTED_WITH='XMLHttpRequest'
		)

	def test_guest_add_returns_updated_count_and_keeps_page_request_json(self):
		response = self.add_item()

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {'cart_count': 1})
		self.assertEqual(
			self.client.session['guest_cart_items'][0]['selected_size'],
			'M'
		)

	def test_repeated_guest_add_increments_quantity(self):
		self.add_item('M')
		response = self.add_item('M')

		self.assertEqual(response.json()['cart_count'], 2)

	def test_invalid_size_is_rejected(self):
		response = self.add_item('XXL')

		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.json()['error'], 'Select a valid size.')

	def test_authenticated_add_saves_selected_size_and_returns_total(self):
		user = get_user_model().objects.create_user(
			username='cart-customer',
			password='test-password'
		)
		self.client.force_login(user)

		response = self.add_item('M')

		self.assertEqual(response.json(), {'cart_count': 1})
		cart = Cart.objects.get(user=user)
		item = CartItem.objects.get(cart=cart)
		self.assertEqual(item.selected_size, 'M')
		self.assertEqual(item.variant, self.variant)
