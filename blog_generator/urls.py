from django.urls import path
from . import views

app_name = 'blog_generator'

urlpatterns = [
    path('', views.index, name='index'),
    path('generate-blog/', views.generate_blog, name='generate-blog'),
    path('blog-list/', views.blog_list, name='blog-list'),
    path('blog-details/<int:pk>/', views.blog_details, name='blog-details'),
    path("delete-selected-blogs/", views.delete_selected_blogs, name="delete-selected-blogs"),
    path("delete-all-blogs/", views.delete_all_blogs, name="delete-all-blogs"),
]
