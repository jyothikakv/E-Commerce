from django.test import TestCase
from django.contrib.auth import get_user_model

from products.models import Category, Product
from .models import WishlistItem


class AddToWishlistTests(TestCase):
	def setUp(self):
		category = Category.objects.create(name='Clothing')
		self.product = Product.objects.create(
			name='Test Shirt',
			category=category,
			description='Test product'
		)

	def add_item(self):
		return self.client.get(
			f'/wishlist/add/{self.product.id}/',
			HTTP_X_REQUESTED_WITH='XMLHttpRequest'
		)

	def test_guest_wishlist_add_updates_count_and_session(self):
		response = self.add_item()

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {
			'wishlist_count': 1,
			'is_wishlisted': True,
		})
		self.assertEqual(
			self.client.session['guest_wishlist_items'],
			[self.product.id]
		)

	def test_second_guest_click_removes_product_and_decrements_count(self):
		self.add_item()
		response = self.add_item()

		self.assertEqual(response.json(), {
			'wishlist_count': 0,
			'is_wishlisted': False,
		})
		self.assertEqual(self.client.session['guest_wishlist_items'], [])

	def test_authenticated_wishlist_click_toggles_product(self):
		user = get_user_model().objects.create_user(
			username='wishlist-customer',
			password='test-password'
		)
		self.client.force_login(user)
		added = self.add_item()
		removed = self.add_item()

		self.assertEqual(added.json(), {
			'wishlist_count': 1,
			'is_wishlisted': True,
		})
		self.assertEqual(removed.json(), {
			'wishlist_count': 0,
			'is_wishlisted': False,
		})
		self.assertEqual(
			WishlistItem.objects.filter(
				wishlist__user=user,
				product=self.product
			).count(),
			0
		)

	def test_guest_wishlisted_product_renders_filled_heart(self):
		self.add_item()
		response = self.client.get('/products/')

		self.assertContains(response, 'aria-pressed="true"')
		self.assertContains(response, 'fa-solid fa-heart')
