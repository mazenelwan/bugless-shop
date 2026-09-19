from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError

from .managers import normalize_customer_email
from .models import User


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "autofocus": True,
                "placeholder": "you@example.com",
            }
        ),
    )
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "placeholder": "Password"}
        ),
    )

    def clean(self):
        email = self.cleaned_data.get("username")
        if email:
            self.cleaned_data["username"] = normalize_customer_email(email)
        return super().clean()


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "autofocus": True,
                "placeholder": "you@example.com",
            }
        )
    )
    first_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(
            attrs={"autocomplete": "given-name", "placeholder": "First name"}
        ),
    )
    last_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(
            attrs={"autocomplete": "family-name", "placeholder": "Last name"}
        ),
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name")

    def clean_email(self):
        email = normalize_customer_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                "An account with this email already exists.",
                code="duplicate_email",
            )
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")
        widgets = {
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
        }

    def clean_email(self):
        email = normalize_customer_email(self.cleaned_data["email"])
        conflict = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if conflict.exists():
            raise ValidationError(
                "An account with this email already exists.",
                code="duplicate_email",
            )
        return email


class NormalizedPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "autofocus": True,
                "placeholder": "you@example.com",
            }
        ),
    )

    def clean_email(self):
        return normalize_customer_email(self.cleaned_data["email"])
