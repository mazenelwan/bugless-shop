from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from .managers import UserManager, normalize_customer_email


class User(AbstractUser):
    username = None
    email = models.EmailField("email address", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_case_insensitive_unique",
            )
        ]

    def clean(self):
        super().clean()
        self.email = normalize_customer_email(self.email)

    def save(self, *args, **kwargs):
        self.email = normalize_customer_email(self.email)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

