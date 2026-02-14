from django.urls import path
from . import views

urlpatterns = [
    # Cities
    path('cities/', views.CityListView.as_view(), name='city-list'),
    path('cities/<slug:slug>/', views.CityDetailView.as_view(), name='city-detail'),

    # Villages
    path('villages/', views.VillageListView.as_view(), name='village-list'),
    path('villages/<slug:slug>/', views.VillageDetailView.as_view(), name='village-detail'),

    # Settings
    path('settings/', views.MainSettingsView.as_view(), name='main-settings'),
]
