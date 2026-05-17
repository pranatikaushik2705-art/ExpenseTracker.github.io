from django.db import models
from django.contrib.auth.models import User
import math
from django.db.models.signals import post_save
from django.dispatch import receiver

class Expense(models.Model):
    CURRENCY_CHOICES = [
        ('INR', 'Indian Rupee (₹)'),
        ('USD', 'US Dollar ($)'),
        ('EUR', 'Euro (€)'),
        ('GBP', 'British Pound (£)'),
        ('JPY', 'Japanese Yen (¥)'),
        ('CAD', 'Canadian Dollar (C$)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='INR')
    category = models.CharField(max_length=100)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_currency_display().split('(')[1][0]} {self.amount} - {self.category}"

    class Meta:
        ordering = ['-date', '-created_at']

class CategoryBudget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=50)
    limit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.IntegerField() 
    year = models.IntegerField()

    def __str__(self):
        return f"{self.user.username} - {self.category} - {self.limit_amount}"

class UserAchievement(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_saved = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    current_streak = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    badges = models.JSONField(default=list) 

    def __str__(self):
        return f"{self.user.username}'s Achievements"

class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=200)
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_live_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    product_url = models.URLField(max_length=500, null=True, blank=True)
    added_date = models.DateTimeField(auto_now_add=True)
    is_tracking = models.BooleanField(default=False)

    def __str__(self):
        return self.item_name

    def calculate_months(self, monthly_savings):
        if not monthly_savings or monthly_savings <= 0:
            return "∞"
        try:
            price = float(self.estimated_price)
            savings = float(monthly_savings)
            result = math.ceil(price / savings)
            return result
        except (ValueError, TypeError):
            return "N/A"

    def calculate_savings_status(self, current_balance, monthly_savings_rate):
        price = float(self.estimated_price)
        balance = float(current_balance)
        savings_rate = float(monthly_savings_rate)

        if balance >= price:
            return "Buy Now! ✅"
        
        remaining_amount = price - balance
        if savings_rate <= 0:
            return "Saving Needed"
            
        months = math.ceil(remaining_amount / savings_rate)
        return f"{months} Month{'s' if months > 1 else ''}"

class Profile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.IntegerField(null=True, blank=True)
    address = models.TextField(max_length=300, null=True, blank=True)
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    occupation = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, default="India")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='O')

    # FIXED INDENTATION HERE
    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()