"""
Library permission classes.

DRF's built-in DjangoModelPermissions does NOT gate GET requests by
default — its perms_map maps GET to an empty list. Our design requires
that a user needs `library.view_<model>` to list or retrieve records.

LibraryModelPermissions extends the DRF class and adds view_ to GET
and HEAD, preserving the default behaviour for the write verbs.
"""
from rest_framework.permissions import DjangoModelPermissions


class LibraryModelPermissions(DjangoModelPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }
