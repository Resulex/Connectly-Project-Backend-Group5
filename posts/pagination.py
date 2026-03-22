from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.conf import settings


class Pagination(PageNumberPagination):
    page_size = settings.REST_FRAMEWORK.get('DEFAULT_PAGE_SIZE', 5)
    page_size_query_param = 'page_size'
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response({
            'total_count': self.page.paginator.count,
            'results': data
        })

