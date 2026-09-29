from django import forms
from .models import Category, Product, ProductVariant
from .models import PriceHistory
from .models import Offer


class PriceHistoryForm(forms.ModelForm):

    class Meta:
        model = PriceHistory

        fields = [
            'variant',
            'price',
            'price_type',
            'start_date',
            'end_date',
        ]

        widgets = {
            'start_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local'
                }
            ),

            'end_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local'
                }
            ),
        }


class OfferForm(forms.ModelForm):

    class Meta:
        model = Offer

        fields = [
            'variant',
            'offer_price',
            'start_date',
            'end_date',
            'is_active',
        ]

        widgets = {

            'start_date': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={
                    'type': 'datetime-local'
                }
            ),

            'end_date': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={
                    'type': 'datetime-local'
                }
            ),

        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['start_date'].input_formats = [
            '%Y-%m-%dT%H:%M'
        ]

        self.fields['end_date'].input_formats = [
            '%Y-%m-%dT%H:%M'
        ]

class CategoryForm(forms.ModelForm):


    class Meta:
        model = Category
        fields = ['name', 'description']


class ProductForm(forms.ModelForm):

    category = forms.CharField(
        max_length=100,
        label='Category',
        required=True
    )

    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'fabric',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        categories = Category.objects.all()

        self.fields['category'] = forms.CharField(
            max_length=100,
            label='Category',
            required=True,
            widget=forms.TextInput(
                attrs={
                    'list': 'category-list',
                    'class': 'form-control',
                    'placeholder': 'Select or type a category'
                }
            )
        )

        self.category_choices = categories


class ProductVariantForm(forms.ModelForm):


    class Meta:
        model = ProductVariant
        fields = [
            'product',
            'size',
            'color',
            'stock',
            'price',
    ]


