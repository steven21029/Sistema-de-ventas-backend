from rest_framework.pagination import PageNumberPagination


class PaginacionAdministrativa(PageNumberPagination):
    page_size = 20
    page_size_query_param = "tamano_pagina"
    max_page_size = 100
