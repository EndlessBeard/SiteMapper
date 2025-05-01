"""
URL configuration for web_django project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from django.conf.urls.static import static
# Import the site_mapper views directly for the root URL
from site_mapper import views as site_mapper_views


urlpatterns = [
    # Point the root URL directly to the site_mapper dashboard
    path("", site_mapper_views.dashboard, name="home_dashboard"),
    # Keep the /site-mapper/ prefix for other site_mapper URLs
    path("site-mapper/", include("site_mapper.urls")),
    # Keep the admin URL
    path('admin/', admin.site.urls),
    # You can optionally remove or comment out the old 'hello' app URL if not needed
    # path("hello/", include("hello.urls")),
]
urlpatterns += staticfiles_urlpatterns()

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
