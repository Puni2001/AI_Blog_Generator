from django.urls import path
from . import views

app_name = 'blog_generator'

urlpatterns = [
    path('', views.index, name='index'),
<<<<<<< HEAD
    path('accounts/login/', views.user_login, name='login'),
    path('accounts/signup/', views.user_signup, name='signup'),
    path('accounts/logout/', views.user_logout, name='logout'),
    path('generate-blog/', views.generate_blog, name='generate-blog'),
    path('blog-list/', views.blog_list, name='blog-list'),
    path('blog-details/<int:pk>/', views.blog_details, name='blog-details'),
    path('delete-selected-blogs/', views.delete_selected_blogs, name="delete-selected-blogs"),
    path('delete-all-blogs/', views.delete_all_blogs, name="delete-all-blogs"),
=======
    path('login/', views.user_login, name='login'),
    path('signup/', views.user_signup, name='signup'),
    path('logout/', views.user_logout, name='logout'),
    path('generate-blog/', views.generate_blog, name='generate-blog'),
    path('blog-list/', views.blog_list, name='blog-list'),
    path('blog-details/<int:pk>/', views.blog_details, name='blog-details'),
    path("delete-selected-blogs/", views.delete_selected_blogs, name="delete-selected-blogs"),
    path("delete-all-blogs/", views.delete_all_blogs, name="delete-all-blogs"),
>>>>>>> temp_branch
]
