from django.urls import path

from . import views


app_name = "accounts"

urlpatterns = [
    path("register/", views.RegistrationView.as_view(), name="register"),
    path("login/", views.AccountLoginView.as_view(), name="login"),
    path("logout/", views.AccountLogoutView.as_view(), name="logout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path(
        "password/change/",
        views.AccountPasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "password/change/done/",
        views.AccountPasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path(
        "password/reset/",
        views.AccountPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password/reset/done/",
        views.AccountPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.AccountPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        views.AccountPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("orders/", views.AccountOrderListView.as_view(), name="order_list"),
    path(
        "orders/<str:number>/",
        views.AccountOrderDetailView.as_view(),
        name="order_detail",
    ),
]
