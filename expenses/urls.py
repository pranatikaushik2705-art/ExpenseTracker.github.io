from django.urls import path
from . import views

urlpatterns = [
    # 1. ROOT PATH (Ye khali hona chahiye taaki direct site khule)
    path('', views.home, name='home'), 
    
    # 2. Auth & Home
    path('welcome/', views.homelogged, name='homelogged'),
    path('login/', views.login_user, name='login'),
    path('register/', views.register_user, name='register'),
    path('logout/', views.logout_user, name='logout'),
    path('forget-password/', views.forget_password, name='forget_password'),
    path('reset-password/', views.reset_password, name='reset_password'),

    # 3. Expenses & Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('list/', views.expense_list, name='expense_list'),
    path('add/', views.add_expense, name='add_expense'),
    path('<int:id>/edit/', views.expense_edit, name='expense_edit'),
    path('expense_delete/', views.expense_delete, name='expense_delete'),
    path('delete-final/', views.confirm_delete, name='confirm_delete'),
    path('set-budget/', views.set_budget, name='set_budget'),
    path('planner/', views.budget_planner, name='planner'),
    path('achievements/', views.achievements_view, name='achievements'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/delete/', views.delete_wishlist_item, name='delete_wishlist_item'),
    path('profile/', views.profile_view, name='profile'),
    path('api/suggest-category/', views.api_suggest_category, name='api_suggest_category'),
    path('add_wish/', views.add_wish, name='add_wish'),
    path('delete-budget/', views.delete_budget, name='delete_budget'),

]
