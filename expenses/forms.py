from django import forms
from .models import Expense
from .models import CategoryBudget

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['amount', 'category', 'date', 'description','user']

class BudgetForm(forms.ModelForm):
    class Meta:
        model = CategoryBudget
        fields = ['category', 'limit_amount']
        
        widgets = {
            'category': forms.TextInput(attrs={
                'class': 'form-input-custom', 
                'placeholder': 'e.g. Food, Travel, Rent...'
            }),
            'limit_amount': forms.NumberInput(attrs={
                'class': 'form-input-custom', 
                'placeholder': 'Enter limit amount (e.g. 5000)'
            }),
        }

    def clean_limit_amount(self):
        """Ensures the budget amount is a positive value."""
        limit_amount = self.cleaned_data.get('limit_amount')
        if limit_amount is not None and limit_amount < 0:
            raise forms.ValidationError("Budget limit cannot be negative.")
        return limit_amount