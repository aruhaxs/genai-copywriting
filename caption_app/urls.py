from django.urls import path
from . import views

urlpatterns = [
    # --- Publik (belum login) ---
    path('', views.landing_page, name='home'),
    path('signup/', views.signup_pengguna, name='signup'),
    path('login/', views.login_pengguna, name='login_user'),

    # --- Wajib login sebagai Pengguna Biasa ---
    path('logout/', views.logout_pengguna, name='logout_user'),
    path('dashboard/', views.generate_caption, name='dashboard'),
    path('instagram/logout/', views.instagram_logout, name='instagram_logout'),

    # --- Alur OAuth Facebook (dipicu dari Admin Panel) ---
    path('facebook/login/', views.facebook_login, name='facebook_login'),
    path('facebook/callback/', views.facebook_callback, name='facebook_callback'),
]