from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

from accounts.models import Address
from cart.models import Cart, CartItem
from products.models import Category, Product, ProductVariant
from .models import Order, OrderItem, ReturnRequest


class BuyNowOrderTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username='order-customer',
			password='test-password'
		)
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
		self.address = Address.objects.create(
			user=self.user,
			full_name='Test Customer',
			phone='5551234567',
			address='1 Test Street',
			city='Test City',
			state='Test State',
			pincode='12345'
		)
		self.client.force_login(self.user)

	def test_buy_now_creates_order_with_selected_size_and_keeps_cart(self):
		cart, _ = Cart.objects.get_or_create(user=self.user)
		CartItem.objects.create(
			cart=cart,
			product=self.product,
			variant=self.variant,
			selected_size='S',
			quantity=2
		)
		session = self.client.session
		session['buy_now_variant_id'] = self.variant.id
		session['buy_now_selected_size'] = 'M'
		session.save()

		response = self.client.post(
			'/orders/place-order/',
			{'selected_address': self.address.id}
		)

		self.assertEqual(response.status_code, 302)
		order_item = OrderItem.objects.get(order__user=self.user)
		self.assertEqual(order_item.selected_size, 'M')
		self.assertEqual(order_item.quantity, 1)
		self.assertEqual(order_item.price, Decimal('100.00'))
		self.variant.refresh_from_db()
		self.assertEqual(self.variant.stock, 3)
		self.assertEqual(CartItem.objects.get(cart=cart).quantity, 2)
		self.assertNotIn('buy_now_variant_id', self.client.session)
		self.assertNotIn('buy_now_selected_size', self.client.session)

	def test_regular_order_clears_cart_items(self):
		cart, _ = Cart.objects.get_or_create(user=self.user)
		CartItem.objects.create(
			cart=cart,
			product=self.product,
			variant=self.variant,
			selected_size='L',
			quantity=1
		)

		response = self.client.post(
			'/orders/place-order/',
			{'selected_address': self.address.id}
		)

		self.assertEqual(response.status_code, 302)
		order_item = OrderItem.objects.get(order__user=self.user)
		self.assertEqual(order_item.selected_size, 'L')
		self.assertFalse(CartItem.objects.filter(cart=cart).exists())
		self.variant.refresh_from_db()
		self.assertEqual(self.variant.stock, 3)

	def test_checkout_rejects_quantity_above_available_stock(self):
		cart, _ = Cart.objects.get_or_create(user=self.user)
		CartItem.objects.create(
			cart=cart,
			product=self.product,
			variant=self.variant,
			selected_size='M',
			quantity=5
		)

		response = self.client.post(
			'/orders/place-order/',
			{'selected_address': self.address.id},
			follow=True
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'no longer have enough stock')
		self.assertFalse(Order.objects.filter(user=self.user).exists())
		self.assertTrue(CartItem.objects.filter(cart=cart).exists())
		self.variant.refresh_from_db()
		self.assertEqual(self.variant.stock, 4)

	def test_cancelling_order_restores_reserved_stock_only_once(self):
		order = Order.objects.create(
			user=self.user,
			full_name=self.address.full_name,
			phone=self.address.phone,
			address=self.address.address,
			city=self.address.city,
			state=self.address.state,
			pincode=self.address.pincode,
			total_amount=Decimal('200.00'),
			status='Pending'
		)
		self.variant.stock = 2
		self.variant.save()
		order_item = OrderItem.objects.create(
			order=order,
			product=self.product,
			variant=self.variant,
			quantity=2,
			price=Decimal('100.00'),
			stock_reserved=True
		)
		admin = get_user_model().objects.create_superuser(
			username='stock-admin',
			email='stock-admin@example.com',
			password='test-password'
		)
		self.client.force_login(admin)

		response = self.client.post(
			reverse('update_order_status', args=[order.uuid]),
			{'status': 'Cancelled'}
		)
		self.assertRedirects(response, reverse('admin_order_detail', args=[order.uuid]))
		self.variant.refresh_from_db()
		order_item.refresh_from_db()
		self.assertEqual(self.variant.stock, 4)
		self.assertTrue(order_item.stock_restored)

		self.client.post(
			reverse('update_order_status', args=[order.uuid]),
			{'status': 'Cancelled'}
		)
		self.variant.refresh_from_db()
		self.assertEqual(self.variant.stock, 4)

	def test_customer_can_view_order_tracking_and_item_details(self):
		order = Order.objects.create(
			user=self.user,
			full_name=self.address.full_name,
			phone=self.address.phone,
			address=self.address.address,
			city=self.address.city,
			state=self.address.state,
			pincode=self.address.pincode,
			total_amount=Decimal('200.00'),
			status='Shipped'
		)
		OrderItem.objects.create(
			order=order,
			product=self.product,
			variant=self.variant,
			selected_size='M',
			quantity=2,
			price=Decimal('100.00')
		)

		response = self.client.get(f'/orders/{order.uuid}/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['order'], order)
		self.assertEqual(response.context['current_status_position'], 2)
		self.assertContains(response, 'Shipped')
		self.assertContains(response, 'Test Shirt')
		self.assertContains(response, 'Size: M')

	def test_customer_cannot_view_another_users_order(self):
		order = Order.objects.create(
			user=self.user,
			full_name=self.address.full_name,
			phone=self.address.phone,
			address=self.address.address,
			city=self.address.city,
			state=self.address.state,
			pincode=self.address.pincode,
			total_amount=Decimal('100.00')
		)
		other_user = get_user_model().objects.create_user(
			username='another-customer',
			password='test-password'
		)
		self.client.force_login(other_user)

		response = self.client.get(f'/orders/{order.uuid}/')

		self.assertEqual(response.status_code, 404)


class ReturnRequestWorkflowTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username='return-customer',
			password='test-password'
		)
		category = Category.objects.create(name='Clothing')
		product = Product.objects.create(
			name='Return Test Shirt',
			category=category,
			description='Test product'
		)
		self.variant = ProductVariant.objects.create(
			product=product,
			size='M',
			price=Decimal('100.00'),
			stock=0
		)
		self.order = Order.objects.create(
			user=self.user,
			full_name='Return Customer',
			phone='5551234567',
			address='1 Test Street',
			city='Test City',
			state='Test State',
			pincode='12345',
			total_amount=Decimal('100.00'),
			status='Delivered'
		)
		OrderItem.objects.create(
			order=self.order,
			product=product,
			variant=self.variant,
			quantity=1,
			price=Decimal('100.00'),
			stock_reserved=True
		)
		self.client.force_login(self.user)

	def test_customer_requests_exchange_and_admin_records_refund_resolution(self):
		response = self.client.get(reverse('order_detail', args=[self.order.uuid]))
		self.assertContains(response, 'Request a return or exchange')

		response = self.client.post(
			reverse('submit_return_request', args=[self.order.uuid]),
			{'requested_remedy': 'exchange', 'reason': 'Wrong size'}
		)
		self.assertRedirects(response, reverse('order_detail', args=[self.order.uuid]))
		return_request = ReturnRequest.objects.get(order=self.order)
		self.assertEqual(return_request.status, 'pending')
		self.assertEqual(return_request.requested_remedy, 'exchange')

		admin_user = get_user_model().objects.create_user(
			username='return-admin',
			password='test-password',
			is_superuser=True
		)
		self.client.force_login(admin_user)
		response = self.client.get(reverse('admin_dashboard'))
		self.assertContains(response, 'Return requests awaiting review: 1')
		response = self.client.get(reverse('admin_orders'))
		self.assertContains(response, 'Pending return requests: 1')
		response = self.client.get(reverse('admin_order_detail', args=[self.order.uuid]))
		self.assertContains(response, 'Return / Exchange Request')

		response = self.client.post(
			reverse('update_return_request', args=[self.order.uuid]),
			{
				'status': 'completed',
				'resolution': 'refund',
				'admin_note': 'Refund has been processed.',
			}
		)
		self.assertRedirects(response, reverse('admin_order_detail', args=[self.order.uuid]))
		return_request.refresh_from_db()
		self.assertEqual(return_request.status, 'completed')
		self.assertEqual(return_request.resolution, 'refund')

		self.client.force_login(self.user)
		response = self.client.get(reverse('order_detail', args=[self.order.uuid]))
		self.assertContains(response, 'Refund money')
		self.assertContains(response, 'Refund has been processed.')

	def test_another_customer_cannot_submit_return_request(self):
		other_user = get_user_model().objects.create_user(
			username='different-customer',
			password='test-password'
		)
		self.client.force_login(other_user)

		response = self.client.post(
			reverse('submit_return_request', args=[self.order.uuid]),
			{'requested_remedy': 'refund', 'reason': 'Changed mind'}
		)

		self.assertEqual(response.status_code, 404)
		self.assertFalse(ReturnRequest.objects.filter(order=self.order).exists())

	def test_admin_restocking_received_return_adds_stock_once(self):
		ReturnRequest.objects.create(
			order=self.order,
			requested_remedy='refund',
			reason='Changed mind'
		)
		admin_user = get_user_model().objects.create_user(
			username='return-stock-admin',
			password='test-password',
			is_superuser=True
		)
		self.client.force_login(admin_user)
		request_url = reverse('update_return_request', args=[self.order.uuid])
		form_data = {
			'status': 'completed',
			'resolution': 'refund',
			'restock_returned_items': 'on',
		}

		response = self.client.post(request_url, form_data)
		self.assertRedirects(response, reverse('admin_order_detail', args=[self.order.uuid]))
		self.variant.refresh_from_db()
		self.assertEqual(self.variant.stock, 1)

		self.client.post(request_url, form_data)
		self.variant.refresh_from_db()
		self.assertEqual(self.variant.stock, 1)
