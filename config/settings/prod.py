from .base import *
from corsheaders.defaults import default_headers

DEBUG = False

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': env.str('DB_NAME'),
#         'USER': env.str('DB_USER'),
#         'PASSWORD': env.str('DB_PASSWORD'),
#         'HOST': env.str('DB_HOST'),
#         'PORT': env.int('DB_PORT'),
#         'ATOMIC_REQUESTS': True,
#     }
# }

STATIC_URL = env.str('STATIC_URL', '/static/')
MEDIA_URL = env.str('MEDIA_URL', '/media/')

CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = True
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=['http://localhost:8000'])
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']
CORS_ALLOW_HEADERS = list(default_headers)

IMGPROXY_BASE_URL="http://img-tourism.foreach.group"