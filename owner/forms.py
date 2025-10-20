from django import forms
from django.contrib.auth.models import User
from .models import Cafe, Staff, MenuItem, MenuCategory  # Add MenuCategory here



class OwnerSignupForm(forms.ModelForm):
    """Form for owner registration"""
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password'
    }))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm Password'
    }), label='Confirm Password')
    phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Phone Number'
    }))
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password != password_confirm:
            raise forms.ValidationError("Passwords do not match")
        
        return cleaned_data


class CafeForm(forms.ModelForm):
    """Form for adding/editing cafes"""
    
    CURRENCY_CHOICES = [
        ('INR', '₹ INR - Indian Rupee'),
        ('USD', '$ USD - US Dollar'),
        ('EUR', '€ EUR - Euro'),
        ('GBP', '£ GBP - British Pound'),
    ]
    
    currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        initial='INR',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Cafe
        fields = ['name', 'address', 'contact', 'email', 'logo', 'open_time', 'close_time', 'tax_percentage', 'currency', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Café Name'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full Address'}),
            'contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91-1234567890'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'cafe@example.com'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'open_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'close_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'tax_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_active': 'Active Status',
            'currency': 'Currency',
        }


class StaffForm(forms.ModelForm):
    """Form for adding/editing staff"""
    class Meta:
        model = Staff
        fields = ['cafe', 'name', 'email', 'phone', 'role', 'status']
        widgets = {
            'cafe': forms.Select(attrs={
                'class': 'form-control'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'staff@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91-1234567890'
            }),
            'role': forms.Select(attrs={
                'class': 'form-control'
            }),
            'status': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ['cafe', 'category', 'name', 'description', 'price', 'image', 'is_available']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter categories based on selected cafe
        if 'cafe' in self.data:
            try:
                cafe_id = int(self.data.get('cafe'))
                self.fields['category'].queryset = MenuCategory.objects.filter(cafe_id=cafe_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.cafe:
            self.fields['category'].queryset = MenuCategory.objects.filter(cafe=self.instance.cafe)
        else:
            self.fields['category'].queryset = MenuCategory.objects.none()
