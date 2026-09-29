import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    phone_number = models.CharField(max_length=15, blank=True)


class Address(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses'
    )

    address_type = models.CharField(max_length=50, blank=True)

    full_name = models.CharField(max_length=150)

    phone = models.CharField(max_length=15)

    address = models.TextField(blank=True, null=True)

    city = models.CharField(max_length=100)

    state = models.CharField(max_length=100)

    pincode = models.CharField(max_length=10)

    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} - {self.city}"