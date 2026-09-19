from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeDoneView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import DetailView, FormView, ListView

from store.models import Order
from store.selectors import customer_orders

from .forms import (
    EmailAuthenticationForm,
    NormalizedPasswordResetForm,
    ProfileForm,
    RegistrationForm,
)
from .throttling import clear_rate_limit, configured_limit, consume_rate_limit


class RateLimitedFormMixin:
    rate_limit_scope = ""
    rate_limit_setting = ""
    rate_limit_identity_field = ""
    clear_rate_limit_on_success = False

    def rate_limit_identity(self):
        if not self.rate_limit_identity_field:
            return ""
        return self.request.POST.get(self.rate_limit_identity_field, "")

    def post(self, request, *args, **kwargs):
        identity = self.rate_limit_identity()
        limited = consume_rate_limit(
            request,
            self.rate_limit_scope,
            identity,
            configured_limit(self.rate_limit_setting),
            settings.ACCOUNT_RATE_LIMIT_WINDOW,
        )
        if limited:
            context = self.get_context_data(
                form=self.get_form_class()(),
                rate_limit_error="Too many attempts. Please try again later.",
            )
            return self.render_to_response(context, status=429)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.clear_rate_limit_on_success:
            clear_rate_limit(
                self.request,
                self.rate_limit_scope,
                self.rate_limit_identity(),
            )
        return response


class RegistrationView(RateLimitedFormMixin, FormView):
    template_name = "accounts/register.html"
    form_class = RegistrationForm
    rate_limit_scope = "register"
    rate_limit_setting = "ACCOUNT_REGISTRATION_RATE_LIMIT"
    clear_rate_limit_on_success = True

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse("accounts:profile"))
        return super().dispatch(request, *args, **kwargs)

    def safe_next_url(self):
        candidate = self.request.POST.get("next") or self.request.GET.get("next", "")
        if candidate and url_has_allowed_host_and_scheme(
            candidate,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return candidate
        return ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next"] = self.safe_next_url()
        return context

    def get_success_url(self):
        return self.safe_next_url() or reverse("accounts:profile")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Your account is ready.")
        return super().form_valid(form)


class AccountLoginView(RateLimitedFormMixin, LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True
    rate_limit_scope = "login"
    rate_limit_setting = "ACCOUNT_LOGIN_RATE_LIMIT"
    rate_limit_identity_field = "username"
    clear_rate_limit_on_success = True


class AccountLogoutView(LoginRequiredMixin, LogoutView):
    http_method_names = ("post", "options")
    next_page = reverse_lazy("store:home")


class ProfileView(LoginRequiredMixin, FormView):
    template_name = "accounts/profile.html"
    form_class = ProfileForm
    success_url = reverse_lazy("accounts:profile")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)


class AccountPasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change_form.html"
    success_url = reverse_lazy("accounts:password_change_done")


class AccountPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"


class AccountPasswordResetView(RateLimitedFormMixin, PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    form_class = NormalizedPasswordResetForm
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")
    rate_limit_scope = "password-reset"
    rate_limit_setting = "ACCOUNT_PASSWORD_RESET_RATE_LIMIT"
    rate_limit_identity_field = "email"


class AccountPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class AccountPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class AccountPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class AccountOrderListView(LoginRequiredMixin, ListView):
    template_name = "accounts/order_list.html"
    context_object_name = "orders"

    def get_queryset(self):
        return customer_orders(self.request.user)


class AccountOrderDetailView(LoginRequiredMixin, DetailView):
    template_name = "accounts/order_detail.html"
    context_object_name = "order"
    slug_field = "number"
    slug_url_kwarg = "number"

    def get_queryset(self):
        return (
            Order.objects.filter(customer=self.request.user)
            .select_related("promotion")
            .prefetch_related("items")
        )
