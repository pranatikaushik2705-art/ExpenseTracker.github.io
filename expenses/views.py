from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, logout, login as auth_login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.urls import reverse
import json
from datetime import datetime, timedelta
import re
from .forms import ExpenseForm, BudgetForm
import calendar
from django.contrib.auth import logout as auth_logout
from django.contrib.messages import get_messages
import math
from .models import Expense, CategoryBudget, WishlistItem
from .models import Profile
from .ai_logic import suggest_category
from django.http import JsonResponse
from .scraper import get_live_price
from .models import CategoryBudget
import requests
import random


# 1. Home logic (Sabse Pehle)

def home(request):
    news_articles = []
    if request.user.is_authenticated:
        api_key = 'd21fcca74b414a02813ffaafd2cc8f0c'
        # Top-headlines for business in India
        url = f'https://newsapi.org/v2/top-headlines?country=in&category=business&apiKey=d21fcca74b414a02813ffaafd2cc8f0c'
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                raw_articles = data.get('articles', [])
                # Filter valid articles
                news_articles = [a for a in raw_articles if a.get('title') and a.get('url')][:3]
        except Exception as e:
            print(f"Connection Error: {e}")

        # --- FALLBACK DATA (Agar API fail ho ya news na mile) ---
        if not news_articles:
            news_articles = [
                {
                    'title': 'Market Monitor: Nifty reaches new milestones in morning trade.',
                    'url': 'https://economictimes.indiatimes.com/',
                    'source': {'name': 'Economic Times'},
                    'urlToImage': None # Trigger unique fallback in HTML
                },
                {
                    'title': 'Smart Saving: Best high-yield accounts for your 2026 goals.',
                    'url': 'https://www.moneycontrol.com/',
                    'source': {'name': 'Wealth News'},
                    'urlToImage': None
                },
                {
                    'title': 'Fintech Update: New AI tools making expense tracking effortless.',
                    'url': 'https://www.business-standard.com/',
                    'source': {'name': 'Tech Insights'},
                    'urlToImage': None
                }
            ]
        
        return render(request, "expenses/homelogged.html", {'news_articles': news_articles})
    
    return render(request, "expenses/home.html")

# 2. Add Expense
@login_required
def add_expense(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        category = request.POST.get("category")
        date = request.POST.get("date")
        description = request.POST.get("description")

        # 1. Basic validation
        if not amount or not category or not date:
            messages.error(request, "All fields except description are required.")
            return redirect("add_expense")

        # --- SMART BUDGET ALERT LOGIC START ---
        try:
            amount_val = float(amount)
            current_month = datetime.now().month
            current_year = datetime.now().year

            # Category wise budget dhoondo
            budget = CategoryBudget.objects.filter(
                user=request.user, 
                category=category, 
                month=current_month,
                year=current_year
            ).first()

            if budget:
                # Is month ka purana total kharcha nikalo is category mein
                total_spent = Expense.objects.filter(
                    user=request.user, 
                    category=category, 
                    date__month=current_month,
                    date__year=current_year
                ).aggregate(Sum('amount'))['amount__sum'] or 0

                # Agar naya kharcha limit cross kar raha hai
                if (float(total_spent) + amount_val) > float(budget.limit_amount):
                    # "ALERT" word zaroori hai base.html mein sound bajane ke liye
                    messages.warning(request, f"⚠️ ALERT: Budget Exceeded for {category}! Limit: ₹{budget.limit_amount}")
        
        except ValueError:
            pass # Agar amount number nahi hai toh skip karein
        # --- SMART BUDGET ALERT LOGIC END ---

        # 2. Expense Save Karein
        Expense.objects.create(
            amount=amount,
            category=category,
            date=date,
            description=description,
            user=request.user
        )
        
        messages.success(request, "Expense Added Successfully!")
        return redirect("expense_list")

    return render(request, "expenses/add_expense.html")
    
@login_required
def add_expense(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        currency = request.POST.get("currency", "INR")
        category = request.POST.get("category", "").strip()
        date = request.POST.get("date")
        description = request.POST.get("description", "").strip()

        if not amount or not date:
            messages.error(request, "Amount and Date are required.")
            return redirect("add_expense")

        try:
            amount_val = float(amount)
            current_month = datetime.now().month
            current_year = datetime.now().year

            # --- IMPROVED SMART AI CATEGORIZATION ---
            # Agar user ne manual category nahi chuni ya "Others" rakha hai
            if not category or category == "Others" or category == "":
                if description:
                    # Naya smart logic call ho raha hai
                    category = suggest_category_v2(description)
                else:
                    category = "Others"

            # --- CONVERSION LOGIC ---
            rates = {'INR': 1.0, 'USD': 83.5, 'EUR': 91.0, 'GBP': 106.0, 'JPY': 0.55}
            rate = rates.get(currency.upper(), 1.0)
            amount_in_inr = amount_val * rate 

            # --- SMART BUDGET ALERT ---
            from .models import CategoryBudget, Expense # Local import errors bachane ke liye
            budget = CategoryBudget.objects.filter(
                user=request.user, 
                category=category, 
                month=current_month,
                year=current_year
            ).first()

            if budget:
                total_spent = Expense.objects.filter(
                    user=request.user, 
                    category=category, 
                    date__month=current_month,
                    date__year=current_year
                ).aggregate(Sum('amount'))['amount__sum'] or 0

                if (float(total_spent) + amount_val) > float(budget.limit_amount):
                    messages.warning(request, f"⚠️ ALERT: Budget Exceeded for {category}!", extra_tags='alert_sound')

            # 2. Save Expense
            Expense.objects.create(
                amount=amount_val,
                currency=currency.upper(),
                category=category,
                date=date,
                description=description,
                user=request.user
            )

            # --- GAMIFICATION & TOAST ---
            expenses_count = Expense.objects.filter(user=request.user).count()
            
            # Agar category "Others" se badal kar kuch aur hui hai toh user ko batayein
            success_msg = f"Expense saved under '{category}'!"
            if description and category != "Others":
                success_msg = f"AI detected '{category}' from your description. Saved! ✨"

            messages.success(request, success_msg)
            return redirect("expense_list")

        except ValueError:
            messages.error(request, "Invalid amount entered.")
            return redirect("add_expense")

    return render(request, "expenses/add_expense.html")

def suggest_category_v2(description):
    desc = description.lower()
    
    # Keyword Dictionary (AI Brain)
    categories = {
        'Food': ['pizza', 'burger', 'zomato', 'swiggy', 'restaurant', 'dinner', 'lunch', 'breakfast', 'tea', 'coffee', 'maggi', 'grocery', 'blinkit', 'zepto'],
        'Transport': ['uber', 'ola', 'auto', 'petrol', 'diesel', 'train', 'flight', 'metro', 'bus', 'fuel'],
        'Entertainment': ['movie', 'netflix', 'prime', 'hotstar', 'cinema', 'game', 'concert', 'ticket'],
        'Shopping': ['amazon', 'flipkart', 'clothes', 'myntra', 'shoes', 'iphone', 'laptop', 'fashion'],
        'Health': ['medicine', 'doctor', 'hospital', 'pharmacy', 'gym', 'health'],
        'Bills': ['recharge', 'electricity', 'rent', 'wifi', 'water', 'gas', 'insurance'],
    }

    for cat, keywords in categories.items():
        if any(word in desc for word in keywords):
            return cat
    
    return "Others" # Agar kuch match na ho

# 3. Expense List
@login_required
def expense_list(request):
    expenses = Expense.objects.filter(user=request.user)
    return render(request, 'expenses/expense_list.html', {'expenses': expenses})

# 4. Edit Expense
@login_required
def expense_edit(request, id):
    expense = get_object_or_404(Expense, id=id, user=request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)
    return render(request, 'expenses/add_expense.html', {'form': form, 'edit': True})

# 5. Delete Expense
@login_required
def expense_delete(request):
    if request.method == "POST":
        expense_id = request.POST.get('expense_id')
        expense = get_object_or_404(Expense, id=expense_id, user=request.user)
        return render(request, 'expenses/delete_expense.html', {'expense': expense})
    return redirect('expense_list')

@login_required
def confirm_delete(request):
    if request.method == "POST":
        expense_id = request.POST.get('expense_id')
        expense = get_object_or_404(Expense, id=expense_id, user=request.user)
        expense.delete()
        messages.success(request, "Expense deleted successfully!")
    return redirect('expense_list')

# 6. Dashboard
@login_required
def dashboard(request):
    expenses = Expense.objects.filter(user=request.user)
    today = datetime.now().date()
    
    # --- 1. SET USER'S BASE CURRENCY ---
    profile = getattr(request.user, 'profile', None)
    
    # User ki country ko clean karke check karna
    # Agar aapne profile mein 'USA' likha hai, toh ye USD uthayega
    raw_country = profile.country.strip().upper() if profile and profile.country else "INDIA"
    
    # Mapping for common inputs
    currency_map = {
        'INDIA': 'INR', 'USA': 'USD', 'US': 'USD', 'UNITED STATES': 'USD',
        'UK': 'GBP', 'UNITED KINGDOM': 'GBP', 'BRITAIN': 'GBP',
        'EUROPE': 'EUR', 'GERMANY': 'EUR', 'FRANCE': 'EUR', 
        'JAPAN': 'JPY', 'CANADA': 'CAD'
    }
    
    user_currency = currency_map.get(raw_country, 'INR') 
    symbols = {'INR': '₹', 'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'CAD': 'C$'}
    user_symbol = symbols.get(user_currency, user_currency)

    # --- 2. CONVERSION RATES (Base: 1 INR) ---
    # In rates ka use karke hum kisi bhi currency se kisi bhi currency mein ja sakte hain
    RATES = {'INR': 1.0, 'USD': 83.5, 'EUR': 91.0, 'GBP': 106.0, 'JPY': 0.55, 'CAD': 61.0}

    def convert_to_user_pref(amount, from_curr):
        amount = float(amount)
        if from_curr == user_currency:
            return amount
        
        # Step A: Pehle original currency se INR mein badlo
        in_inr = amount * RATES.get(from_curr, 1.0)
        
        # Step B: Phir INR se user ki pasandida currency (e.g. USD) mein badlo
        target_rate = RATES.get(user_currency, 1.0)
        return in_inr / target_rate

    # --- 3. FILTER LOGIC ---
    selected_month = int(request.GET.get('month', today.month))
    selected_year = int(request.GET.get('year', today.year))
    month_expenses = expenses.filter(date__month=selected_month, date__year=selected_year)
    
    # Total for the month in User's Currency
    month_total = sum(convert_to_user_pref(e.amount, e.currency) for e in month_expenses)

    # --- 4. WEEKLY TRENDS (Converted) ---
    if selected_month == today.month and selected_year == today.year:
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = today
    else:
        last_day_of_month = calendar.monthrange(selected_year, selected_month)[1]
        end_of_week = datetime(selected_year, selected_month, last_day_of_month).date()
        start_of_week = end_of_week - timedelta(days=6)

    this_week_qs = expenses.filter(date__range=[start_of_week, end_of_week])
    this_week_total = sum(convert_to_user_pref(e.amount, e.currency) for e in this_week_qs)
    
    last_week_start = start_of_week - timedelta(days=7)
    last_week_end = start_of_week - timedelta(days=1)
    last_week_qs = expenses.filter(date__range=[last_week_start, last_week_end])
    last_week_total = sum(convert_to_user_pref(e.amount, e.currency) for e in last_week_qs)

    weekly_diff = float(this_week_total) - float(last_week_total)
    weekly_status = "up" if weekly_diff > 0 else "down"

    # Weekly Chart Data
    week_days = []
    week_amounts = []
    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        day_expenses = expenses.filter(date=current_day)
        day_total = sum(convert_to_user_pref(e.amount, e.currency) for e in day_expenses)
        week_days.append(current_day.strftime("%a %d"))
        week_amounts.append(round(day_total, 2))

    # --- 5. CATEGORY & TREND DATA ---
    cat_totals = {}
    for e in month_expenses:
        val = convert_to_user_pref(e.amount, e.currency)
        cat_totals[e.category] = cat_totals.get(e.category, 0) + val
    
    categories = list(cat_totals.keys())
    totals = [round(v, 2) for v in cat_totals.values()]

    date_totals = {}
    for e in month_expenses:
        d_str = e.date.strftime("%Y-%m-%d")
        date_totals[d_str] = date_totals.get(d_str, 0) + convert_to_user_pref(e.amount, e.currency)
    
    dates = sorted(date_totals.keys())
    amount_over_time = [round(date_totals[d], 2) for d in dates]

    # --- 6. BUDGET PROGRESS ---
    user_budgets = CategoryBudget.objects.filter(user=request.user, month=selected_month, year=selected_year)
    budget_progress = []
    over_budget_cats = []
    for b in user_budgets:
        spent_converted = cat_totals.get(b.category, 0)
        # Budget limit hum user ki base currency mein hi maan rahe hain
        percent = (float(spent_converted) / float(b.limit_amount)) * 100 if b.limit_amount > 0 else 0
        if spent_converted > float(b.limit_amount): over_budget_cats.append(b.category)
        budget_progress.append({
            'category': b.category, 'limit': b.limit_amount, 'spent': round(spent_converted, 2),
            'percent': min(percent, 100),
            'color': 'danger' if percent >= 100 else 'success'
        })

    # --- 7. HEATMAP ---
    num_days = calendar.monthrange(selected_year, selected_month)[1]
    heatmap_data = []
    # Thresholds logic (converted to user pref)
    high_th = convert_to_user_pref(2000, 'INR')
    med_th = convert_to_user_pref(500, 'INR')

    for day in range(1, num_days + 1):
        daily_val = sum(convert_to_user_pref(e.amount, e.currency) for e in month_expenses.filter(date__day=day))
        color = "high" if daily_val > high_th else "medium" if daily_val > med_th else "low" if daily_val > 0 else "empty"
        heatmap_data.append({'day': day, 'total': round(daily_val, 2), 'color': color})

    # --- 8. TIPS ---
    tips = []
    diff_abs = abs(round(weekly_diff, 2))
    if last_week_total > 0:
        if weekly_status == "up":
            tips.append(f"⚠️ Spending alert: Up by {user_symbol}{diff_abs} vs last week.")
        else:
            tips.append(f"✅ Great job! Saved {user_symbol}{diff_abs} vs last week.")
    if over_budget_cats:
        tips.append(f"🚫 Budget exceeded for: {', '.join(over_budget_cats)}.")
    if not tips:
        tips.append(f"✨ Monthly total: {user_symbol}{round(month_total, 2)}. Keep tracking!")

    context = {
        "this_week_total": round(this_week_total, 2), "last_week_total": round(last_week_total, 2),
        "weekly_diff": diff_abs, "weekly_status": weekly_status,
        "week_days_json": json.dumps(week_days), "week_amounts_json": json.dumps(week_amounts),
        "month_total": round(month_total, 2), "month_name": calendar.month_name[selected_month],
        "categories_json": json.dumps(categories), "totals_json": json.dumps(totals),
        "dates_json": json.dumps(dates), "amount_json": json.dumps(amount_over_time),
        "heatmap_data": heatmap_data, "budget_progress": budget_progress,
        "selected_month": selected_month, "selected_year": selected_year,
        "months_choices": [(i, calendar.month_name[i]) for i in range(1, 13)],
        "years_choices": range(today.year - 2, today.year + 2),
        "personalized_tips": tips,
        "user_symbol": user_symbol,
    }
    return render(request, "expenses/dashboard.html", context)

# 7. Login

def login_user(request):
    if request.method == "POST":
        # 1. PEHLE PURANE MESSAGES CLEAR KARO
        # Taaki logout wala message login hone par dashboard pe na dikhe
        storage = get_messages(request)
        for _ in storage:
            pass 

        email = request.POST.get("email_from_firebase")
        
        if email:
            # Sync Firebase User with Django
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': email.split('@')[0].title() 
                }
            )

            # 2. Start Django Session
            auth_login(request, user)
            
            # 3. FRESH WELCOME MESSAGE (Professional English)
            display_name = user.first_name if user.first_name else user.username
            messages.success(request, f"Welcome back, {display_name}!")
            
            return redirect('homelogged') 

        else:
            # Error feedback
            messages.error(request, "Authentication failed. Please try again.")
            return redirect('login')

    return render(request, "expenses/login.html")

@login_required(login_url='login')
def homelogged(request):
    # Ab ye page khulega kyunki auth_login ne session bana diya hai
    return render(request, "expenses/homelogged.html")


def logout_user(request):
    auth_logout(request)
    # Humne success message hata diya hai taaki agle login par ye "ghost toast" na aaye
    return redirect("login")

# 9. Register
def register_user(request):
    if request.method == "POST":
        full_name = request.POST.get("username") 
        email = request.POST.get("email")
        pass1 = request.POST.get("password")
        pass2 = request.POST.get("password2")

        # 1. Basic Fields Check
        if not all([full_name, email, pass1, pass2]):
            messages.error(request, "Please fill all the fields!")
            return redirect("register")

        if pass1 != pass2:
            messages.error(request, "Passwords do not match!")
            return redirect("register")

        # 2. Password Hardcore Validation
        if len(pass1) < 8:
            messages.error(request, "Password must be at least 8 characters long!")
            return redirect("register")
        if not re.search(r'[A-Z]', pass1):
            messages.error(request, "Password must contain at least one uppercase letter!")
            return redirect("register")
        if not re.search(r'[0-9]', pass1):
            messages.error(request, "Password must contain at least one digit!")
            return redirect("register")

        # 3. Duplicate Email Check
        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered!")
            return redirect("register")

        # 4. Create User & Unique Username Generation
        base_username = email.split('@')[0]
        final_username = base_username
        counter = 1
        while User.objects.filter(username=final_username).exists():
            final_username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(username=final_username, email=email, password=pass1)
        user.first_name = full_name.title() 
        user.save()

        # 5. Success Message & Redirect
        messages.success(request, f"Welcome {user.first_name}! Your account has been created. Please log in.")
        return redirect("login") 
        
    return render(request, "expenses/register.html")

# 10. Forget Password
def forget_password(request):
    if request.method == "POST":
        username = request.POST.get("username")
        if not User.objects.filter(username=username).exists():
            messages.error(request, "User does not exist!")
            return redirect("forget_password")
        
        return redirect(f"{reverse('reset_password')}?username={username}")
    return render(request, "expenses/forget_password.html")

# 11. Reset Password
def reset_password(request):
    username = request.GET.get("username") or request.POST.get("username")
    if not User.objects.filter(username=username).exists():
        messages.error(request, "Invalid user")
        return redirect("forget_password")

    if request.method == "POST":
        pass1 = request.POST.get("password")
        pass2 = request.POST.get("password2")
        if pass1 != pass2:
            messages.error(request, "Passwords do not match!")
            return render(request, "expenses/reset_password.html", {"username": username})

        user = User.objects.get(username=username)
        user.set_password(pass1)
        user.save()
        messages.success(request, "Password changed! Please login.")
        return redirect("login")
    return render(request, "expenses/reset_password.html", {"username": username})

@login_required
def set_budget(request):
    now = datetime.now()
    
    if request.method == "POST":
        category_name = request.POST.get('category')
        limit_amount = float(request.POST.get('limit_amount', 0))
        
        existing_budget = CategoryBudget.objects.filter(
            user=request.user, category__iexact=category_name, 
            month=now.month, year=now.year
        ).first()

        form = BudgetForm(request.POST, instance=existing_budget)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.month = now.month
            budget.year = now.year
            budget.save()
            
            # Check for buzzer
            agg = Expense.objects.filter(
                user=request.user, category__iexact=category_name,
                date__month=now.month, date__year=now.year
            ).aggregate(total=Sum('amount'))
            total_spent = float(agg['total'] or 0)

            if total_spent > limit_amount:
                messages.warning(request, f"Limit Exceeded for {category_name}!", extra_tags='play-buzzer')
            else:
                messages.success(request, f"Limit for {category_name} updated!")
            return redirect('set_budget')

    # GET data
    active_budgets = CategoryBudget.objects.filter(user=request.user, month=now.month, year=now.year)
    total_budget_limit = active_budgets.aggregate(Sum('limit_amount'))['limit_amount__sum'] or 0
    form = BudgetForm()
    
    return render(request, 'expenses/set_budget.html', {
        'form': form,
        'active_budgets': active_budgets,
        'total_limit': total_budget_limit,
    })

@login_required
def budget_planner(request):
    today = datetime.now().date()
    selected_month = int(request.GET.get('month', today.month))
    selected_year = int(request.GET.get('year', today.year))

    # Fetch total expenses for selected month
    total_spent = Expense.objects.filter(
        user=request.user, 
        date__month=selected_month, 
        date__year=selected_year
    ).aggregate(Sum("amount"))["amount__sum"] or 0

    # Income handle (Abhi ke liye query params se le rahe hain, 
    # baad mein ise Profile model mein save bhi kar sakte hain)
    income = float(request.GET.get('income', 0))
    
    balance = income - float(total_spent)
    savings_percent = (balance / income * 100) if income > 0 else 0
    
    # Days left in month logic
    last_day = calendar.monthrange(selected_year, selected_month)[1]
    days_left = last_day - today.day if selected_month == today.month else 0
    daily_budget = balance / days_left if days_left > 0 and balance > 0 else 0

    context = {
        'total_spent': total_spent,
        'income': income,
        'balance': balance,
        'savings_percent': round(savings_percent, 1),
        'daily_budget': round(daily_budget, 2),
        'days_left': days_left,
        'selected_month': selected_month,
        'month_name': calendar.month_name[selected_month],
    }
    return render(request, "expenses/planner.html", context)

@login_required
def achievements_view(request):
    user = request.user
    today = datetime.now().date()
    seven_days_ago = today - timedelta(days=7)
    fourteen_days_ago = today - timedelta(days=14)

    # --- 1. GET USER CURRENCY FROM PROFILE ---
    profile = getattr(user, 'profile', None)
    raw_country = profile.country.strip().upper() if profile and profile.country else "INDIA"
    
    currency_map = {
        'INDIA': 'INR', 'USA': 'USD', 'UK': 'GBP', 'EUROPE': 'EUR', 'JAPAN': 'JPY'
    }
    user_currency = currency_map.get(raw_country, 'INR')
    symbols = {'INR': '₹', 'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥'}
    user_symbol = symbols.get(user_currency, user_currency)

    # Conversion Rates (Base: 1 INR)
    RATES = {'INR': 1.0, 'USD': 83.5, 'EUR': 91.0, 'GBP': 106.0, 'JPY': 0.55}

    def convert_to_user_pref(amount, from_curr):
        amount = float(amount or 0)
        if from_curr == user_currency:
            return amount
        # INR mein badlo, phir target currency mein
        in_inr = amount * RATES.get(from_curr, 1.0)
        return in_inr / RATES.get(user_currency, 1.0)

    # --- 2. CALCULATE SPENDING (Converted) ---
    def get_converted_total(queryset):
        total = 0
        for e in queryset:
            total += convert_to_user_pref(e.amount, e.currency)
        return total

    current_week_qs = Expense.objects.filter(user=user, date__range=[seven_days_ago, today])
    last_week_qs = Expense.objects.filter(user=user, date__range=[fourteen_days_ago, seven_days_ago])
    all_time_qs = Expense.objects.filter(user=user)

    current_week_total = get_converted_total(current_week_qs)
    last_week_total = get_converted_total(last_week_qs)
    total_all_time = get_converted_total(all_time_qs)

    # --- 3. DYNAMIC BADGES LOGIC ---
    unlocked_badges = []
    
    # Milestone threshold (e.g. 1000 INR converted to User Pref)
    # Agar user USA mein hai, toh ye approx $12 ka milestone banega
    milestone_base = 1000 
    milestone_converted = convert_to_user_pref(milestone_base, 'INR')

    if total_all_time >= milestone_converted:
        unlocked_badges.append({
            'name': 'Budget Boss', 
            'icon': '🎖️', 
            'desc': f'Managed over {user_symbol}{int(milestone_converted)} all-time!'
        })
    
    if current_week_total < last_week_total and last_week_total > 0:
        unlocked_badges.append({
            'name': 'Efficiency Pro', 
            'icon': '📈', 
            'desc': 'Spending is lower than last week. Great trend!'
        })
    
    if current_week_total == 0 and all_time_qs.exists():
        unlocked_badges.append({
            'name': 'Zen Mode', 
            'icon': '🧘', 
            'desc': 'Zero spending recorded this week!'
        })

    context = {
        'badges': unlocked_badges,
        'current_week': round(current_week_total, 2),
        'last_week': round(last_week_total, 2),
        'user_symbol': user_symbol,
        'streak': 5, # Placeholder for your logic
    }
    return render(request, 'expenses/achievements.html', context)

@login_required
def wishlist_view(request):
    # 1. Profile aur Gender Fetch karna
    profile, created = Profile.objects.get_or_create(user=request.user)
    current_gender = str(profile.gender).upper() if profile.gender else 'O'

    # 2. THEME ENGINE: Colors yahi se decide honge
    if current_gender == 'M':
        # Boy Theme: Blue
        theme_color = "linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)"
        accent_color = "#3b82f6"
        text_color = "#1e3a8a"
        bg_card = "rgba(239, 246, 255, 0.8)" # Light Blue Glass
    elif current_gender == 'F':
        # Girl Theme: Pink
        theme_color = "linear-gradient(135deg, #9d174d 0%, #ec4899 100%)"
        accent_color = "#ec4899"
        text_color = "#9d174d"
        bg_card = "rgba(255, 241, 242, 0.8)" # Light Pink Glass
    else:
        # Default Theme: Neutral/Slate
        theme_color = "linear-gradient(135deg, #0f172a 0%, #334155 100%)"
        accent_color = "#64748b"
        text_color = "#0f172a"
        bg_card = "rgba(255, 255, 255, 0.9)"

    # 3. Currency Symbol Mapping
    symbols = {'INDIA': '₹', 'USA': '$', 'UK': '£', 'EUROPE': '€', 'JAPAN': '¥'}
    user_symbol = symbols.get(profile.country.upper() if profile.country else 'INDIA', '₹')

    # 4. Wishlist Items Fetch karna
    items = WishlistItem.objects.filter(user=request.user).order_by('-id')

    # 5. Business Logic (Savings & Timeline)
    # Maan lo hum 10% saving man ke chal rahe hain agar income set hai toh
    monthly_income = float(profile.monthly_income or 0)
    monthly_savings = monthly_income * 0.2  # 20% savings assumption (Aap apna logic yahan daal sakte ho)
    
    if monthly_savings <= 0: monthly_savings = 1000 # Default fallback

    for item in items:
        # Progress & Timeline Calculation
        price = float(item.estimated_price or 0)
        if price > 0:
            months = price / monthly_savings
            item.months_needed = round(months, 1)
            # Progress bar % (Simple logic: savings vs price)
            item.progress_pct = min(round((monthly_savings / price) * 100, 1), 100)
        else:
            item.months_needed = 0
            item.progress_pct = 0

    # 6. Context Packing
    context = {
        'wishlist_items': items,
        'user_symbol': user_symbol,
        'gender': current_gender,
        'theme_color': theme_color,
        'accent_color': accent_color,
        'text_color': text_color,
        'bg_card': bg_card,
        'status_msg': "Theme & Data Synchronized"
    }
    
    return render(request, 'expenses/wishlist.html', context)
    
@login_required
def delete_wishlist_item(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        item = get_object_or_404(WishlistItem, id=item_id, user=request.user)
        item.delete()
        messages.success(request, "Goal removed successfully.")
    return redirect('wishlist')

@login_required
def profile_view(request):
    if request.method == "POST":
        # 1. User Table Update
        u = request.user
        u.first_name = request.POST.get('first_name', u.first_name)
        u.last_name = request.POST.get('last_name', u.last_name)
        u.save()

        # 2. Profile Table Update
        country_val = request.POST.get('country', 'INDIA').strip().upper()
        income_val = request.POST.get('income', 0.0)
        gender_val = request.POST.get('gender', 'O') # <--- Gender catch kiya
        
        # Gender mapping for better Toast message
        gender_names = {'M': 'Male', 'F': 'Female', 'O': 'Other'}
        selected_gender_name = gender_names.get(gender_val, 'Other')

        Profile.objects.update_or_create(
            user=request.user,
            defaults={
                'country': country_val,
                'monthly_income': float(income_val) if income_val else 0.0,
                'age': int(request.POST.get('age')) if request.POST.get('age') else None,
                'address': request.POST.get('address', ''),
                'occupation': request.POST.get('occupation', ''),
                'gender': gender_val, # <--- YE SABSE ZAROORI LINE HAI
            }
        )
        
        # Ek badhiya Dynamic Message
        messages.success(request, f"Profile & {selected_gender_name} Theme Updated! ✅")
        return redirect('profile')

    # GET Request Logic
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    # Mapping
    symbols = {'INDIA': '₹', 'USA': '$', 'UK': '£', 'EUROPE': '€', 'JAPAN': '¥'}
    current_symbol = symbols.get(profile.country.upper(), '₹')
    
    return render(request, 'expenses/profile.html', {
        'profile': profile,
        'user_symbol': current_symbol
    })
    
def api_suggest_category(request):
    description = request.GET.get('description', '')
    if description:
        prediction = suggest_category(description)
        return JsonResponse({'suggestion': prediction})
    return JsonResponse({'suggestion': 'Others'})


@login_required
def add_wish(request):
    if request.method == 'POST':
        name = request.POST.get('item_name')
        price = request.POST.get('price')
        
        if name and price:
            # Yahan check karo tumhare Model ka naam 'WishlistItem' hai ya kuch aur
            WishlistItem.objects.create(
                user=request.user, 
                item_name=name, 
                estimated_price=price
            )
            return redirect('wishlist') # Deleting ke baad wapas wishlist pe le jayega
    return redirect('wishlist')

@login_required
def delete_budget(request):
    if request.method == "POST":
        budget_id = request.POST.get('id')
        budget = get_object_or_404(CategoryBudget, id=budget_id, user=request.user)
        category = budget.category
        budget.delete()
        return JsonResponse({
            'status': 'success', 
            'message': f'Budget for {category} has been removed.'
        })
    return JsonResponse({'status': 'error'}, status=400)

def home(request):
    news_articles = []
    if request.user.is_authenticated:
        api_key = 'd21fcca74b414a02813ffaafd2cc8f0c'
        # Top-headlines for business in India
        url = f'https://newsapi.org/v2/top-headlines?country=in&category=business&apiKey=d21fcca74b414a02813ffaafd2cc8f0c'
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                raw_articles = data.get('articles', [])
                # Filter valid articles
                news_articles = [a for a in raw_articles if a.get('title') and a.get('url')][:3]
        except Exception as e:
            print(f"Connection Error: {e}")

        # --- FALLBACK DATA (Agar API fail ho ya news na mile) ---
        if not news_articles:
            news_articles = [
                {
                    'title': 'Market Monitor: Nifty reaches new milestones in morning trade.',
                    'url': 'https://economictimes.indiatimes.com/',
                    'source': {'name': 'Economic Times'},
                    'urlToImage': None # Trigger unique fallback in HTML
                },
                {
                    'title': 'Smart Saving: Best high-yield accounts for your 2026 goals.',
                    'url': 'https://www.moneycontrol.com/',
                    'source': {'name': 'Wealth News'},
                    'urlToImage': None
                },
                {
                    'title': 'Fintech Update: New AI tools making expense tracking effortless.',
                    'url': 'https://www.business-standard.com/',
                    'source': {'name': 'Tech Insights'},
                    'urlToImage': None
                }
            ]
        
        return render(request, "expenses/homelogged.html", {'news_articles': news_articles})
    
    return render(request, "expenses/home.html")