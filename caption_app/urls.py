from django.urls import path
from . import views

urlpatterns = [
    path('', views.generate_caption, name='home'),
    path('facebook/login/', views.facebook_login, name='facebook_login'),
    path('facebook/callback/', views.facebook_callback, name='facebook_callback'),
]