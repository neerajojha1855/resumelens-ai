from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_resume, name='upload_resume'),
    path('results/<int:pk>/', views.results, name='results'),
    path('api/auth/login/', views.firebase_login, name='firebase_login'),
    path('api/auth/logout/', views.firebase_logout, name='firebase_logout'),
]
