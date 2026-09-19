from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError


CATALOG_PERMISSIONS = {
    "view_category",
    "add_category",
    "change_category",
    "view_product",
    "add_product",
    "change_product",
    "delete_product",
    "view_productimage",
    "add_productimage",
    "change_productimage",
    "delete_productimage",
    "view_productvariant",
    "add_productvariant",
    "change_productvariant",
    "delete_productvariant",
    "view_promotion",
    "add_promotion",
    "change_promotion",
    "view_homecontent",
    "add_homecontent",
    "change_homecontent",
}

FULFILLMENT_PERMISSIONS = {
    "view_order",
    "view_orderitem",
    "view_orderevent",
    "view_product",
    "view_productvariant",
    "transition_order",
}

SUPPORT_PERMISSIONS = {
    "view_order",
    "view_orderitem",
    "view_orderevent",
    "view_contactmessage",
    "view_contactmessageevent",
}

MANAGER_PERMISSIONS = (
    CATALOG_PERMISSIONS
    | FULFILLMENT_PERMISSIONS
    | SUPPORT_PERMISSIONS
    | {
        "cancel_order",
    }
)

ROLE_PERMISSIONS = {
    "Catalog Manager": CATALOG_PERMISSIONS,
    "Fulfillment Staff": FULFILLMENT_PERMISSIONS,
    "Customer Support": SUPPORT_PERMISSIONS,
    "Store Manager": MANAGER_PERMISSIONS,
}


class Command(BaseCommand):
    help = "Create or reconcile the least-privilege Bugless Fit staff groups."

    def handle(self, *args, **options):
        required_codenames = set().union(*ROLE_PERMISSIONS.values())
        permissions = {
            permission.codename: permission
            for permission in Permission.objects.filter(
                content_type__app_label="store",
                codename__in=required_codenames,
            ).select_related("content_type")
        }
        missing = sorted(required_codenames - permissions.keys())
        if missing:
            raise CommandError(
                "Store permissions are missing. Run migrations first: " + ", ".join(missing)
            )

        for role_name, codenames in ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=role_name)
            group.permissions.set(permissions[codename] for codename in sorted(codenames))
            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action} {role_name} with {len(codenames)} permissions."
                )
            )
