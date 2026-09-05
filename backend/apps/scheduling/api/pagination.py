"""Pagination utilities for scheduling API."""

from rest_framework.pagination import PageNumberPagination


class SchedulingRunPagination(PageNumberPagination):
    """
    Paginate scheduling runs to avoid memory exhaustion.
    
    Default: 50 runs per page. Configurable via ?page_size=100
    """
    
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class TimetableEntryPagination(PageNumberPagination):
    """
    Paginate timetable entries when listing all versions.
    
    Default: 100 entries per page.
    """
    
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500
