import re

from django import forms


def validate_phone(phone):
    phone = phone.strip()
    if not phone:
        return ""
    if not re.fullmatch(r"\+?[0-9() \-]+", phone):
        raise forms.ValidationError(
            "Use only digits, spaces, parentheses, hyphens, and an optional leading +.",
            code="invalid_phone",
        )
    digit_count = len(re.sub(r"[^0-9]", "", phone))
    if digit_count < 7 or digit_count > 15:
        raise forms.ValidationError(
            "Enter a phone number containing 7 to 15 digits.",
            code="invalid_phone_length",
        )
    return phone


class CheckoutCustomerForm(forms.Form):
    name = forms.CharField(max_length=160)
    email = forms.EmailField(max_length=254)
    phone = forms.CharField(max_length=40)
    address = forms.CharField(max_length=500)
    city = forms.CharField(max_length=100, required=False)
    notes = forms.CharField(max_length=2000, required=False)

    def clean_email(self):
        return self.cleaned_data["email"].strip().casefold()

    def clean_phone(self):
        return validate_phone(self.cleaned_data["phone"])


class ContactForm(forms.Form):
    submission_id = forms.UUIDField(widget=forms.HiddenInput)
    name = forms.CharField(max_length=160)
    email = forms.EmailField(max_length=254)
    phone = forms.CharField(max_length=40, required=False)
    subject = forms.CharField(max_length=200, required=False)
    message = forms.CharField(max_length=5000, widget=forms.Textarea)
    website = forms.CharField(max_length=200, required=False)

    def clean_email(self):
        return self.cleaned_data["email"].strip().casefold()

    def clean_phone(self):
        return validate_phone(self.cleaned_data["phone"])

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("website"):
            raise forms.ValidationError(
                "We could not send your message. Refresh the page and try again.",
                code="honeypot",
            )
        return cleaned_data
