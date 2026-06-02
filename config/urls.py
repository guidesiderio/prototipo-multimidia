from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("usuarios.urls")),
    # a raiz redireciona para o dashboard (que exige login)
    path("", RedirectView.as_view(pattern_name="dashboard")),
]

# serve os arquivos de media durante o desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
