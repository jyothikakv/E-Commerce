from django.utils import timezone
from products.models import Product, Offer
from django.shortcuts import render
from products.models import Product

from .models import ContactMessage


def home(request):

    products = Product.objects.all().order_by('-created_at')[:4]

    for product in products:

        product.display_image_url = None

        for variant in product.variants.all():

            first_image = variant.images.first()

            if first_image and first_image.image:
                product.display_image_url = first_image.image.url
                break

        if not product.display_image_url and product.image:
            product.display_image_url = product.image.url

    current_time = timezone.now()

    offers = list(Offer.objects.filter(
        is_active=True,
        start_date__lte=current_time,
        end_date__gte=current_time
    ).select_related('variant', 'variant__product').order_by('-start_date')[:4])

    if len(offers) < 4:
        active_variant_ids = [offer.variant_id for offer in offers]
        ended_offers = Offer.objects.filter(
            is_active=True,
            start_date__lte=current_time,
            end_date__lt=current_time
        ).exclude(
            variant_id__in=active_variant_ids
        ).select_related(
            'variant',
            'variant__product'
        ).order_by('-end_date')[:4 - len(offers)]
        offers.extend(ended_offers)

    for offer in offers:
        offer.is_currently_active = (
            offer.is_active
            and offer.start_date <= current_time <= offer.end_date
        )

    return render(
        request,
        'home/home.html',
        {
            'products': products,
            'offers': offers,
        }
    )


def contact(request):

    if request.method == 'POST':

        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        return render(
            request,
            'home/contact.html',
            {'success': 'Your message has been sent successfully!'}
        )

    return render(request, 'home/contact.html')


def categories(request):
    return render(request, 'home/home.html')