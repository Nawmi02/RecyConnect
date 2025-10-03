"""
URL configuration for Recycle project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path("", views.landingPage, name="landingPage"),
    path("user/", include(("User.urls", "user"), namespace="user")),
    path("panel/", include(("AdminPanel.urls", "adminpanel"), namespace="adminpanel")),
    path("household/", include(("Household.urls", "household"), namespace="household")),
    path("collector/", include(("Collector.urls", "collector"), namespace="collector")),
    path("buyer/", include(("Buyer.urls", "buyer"), namespace="buyer")),
    path("education/", include(("Education.urls", "education"), namespace="education")),
    path("marketplace/", include(("Marketplace.urls", "marketplace"), namespace="marketplace")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
