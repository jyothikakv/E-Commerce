from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Address


class RegisterForm(UserCreationForm):

    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'password1',
            'password2',
        ]


class AddressForm(forms.ModelForm):

    class Meta:
        model = Address
        fields = [
            'address_type',
            'full_name',
            'phone',
            'address',
            'city',
            'state',
            'pincode',
            'is_default',
        ]