from django.urls import re_path
from rest_framework import permissions
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from drf_yasg.generators import OpenAPISchemaGenerator


class HttpAndHttpsSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema.schemes = ['https', 'http']
        return schema


schema_view = get_schema_view(
    openapi.Info(
        title='Tourism Villages API',
        default_version='v1',
        description='API for Tourism Villages — cities, villages, gallery, comments, and settings.',
    ),
    public=True,
    generator_class=HttpAndHttpsSchemaGenerator,
    permission_classes=(permissions.AllowAny,),
)

swagger_urlpatterns = [
    re_path(
        r'^api/swagger(?P<format>\.json|\.yaml)$',
        schema_view.without_ui(cache_timeout=0),
        name='schema-json',
    ),
    re_path(
        r'^api/swagger/$',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui',
    ),
    re_path(
        r'^api/redoc/$',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc',
    ),
]
