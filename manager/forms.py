from django import forms
from owner.models import Order, Table, MenuItem, MenuCategory


class OrderFilterForm(forms.Form):
    """Form for filtering orders in the order management view"""
    
    STATUS_CHOICES = [
        ('all', 'All Orders'),
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    DATE_CHOICES = [
        ('today', 'Today'),
        ('yesterday', 'Yesterday'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('all', 'All Time'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        initial='all',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit()'
        })
    )
    
    date_range = forms.ChoiceField(
        choices=DATE_CHOICES,
        required=False,
        initial='today',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit()'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search order number or table...'
        })
    )


class TableStatusForm(forms.ModelForm):
    """Form for updating table status"""
    
    class Meta:
        model = Table
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        labels = {
            'status': 'Table Status'
        }


class QuickOrderForm(forms.Form):
    """Quick order form for POS system"""
    
    ORDER_TYPE_CHOICES = [
        ('dine_in', 'Dine In'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery'),
    ]
    
    table = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'tableSelect'
        }),
        label='Select Table'
    )
    
    order_type = forms.ChoiceField(
        choices=ORDER_TYPE_CHOICES,
        initial='dine_in',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'orderType',
            'onchange': 'toggleTableSelect()'
        }),
        label='Order Type'
    )
    
    def __init__(self, cafe=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if cafe:
            # Dynamically populate table choices based on cafe
            tables = Table.objects.filter(cafe=cafe, status='available').order_by('table_number')
            self.fields['table'].choices = [('', 'Choose a table...')] + [
                (table.id, f"Table {table.table_number} ({table.capacity} seats)") 
                for table in tables
            ]


class MenuSearchForm(forms.Form):
    """Form for searching menu items"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search menu items...',
            'id': 'searchMenu'
        }),
        label=''
    )
    
    category = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit()'
        }),
        label='Category'
    )
    
    availability = forms.ChoiceField(
        required=False,
        choices=[
            ('all', 'All Items'),
            ('available', 'Available Only'),
            ('unavailable', 'Out of Stock'),
        ],
        initial='all',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit()'
        }),
        label='Availability'
    )
    
    def __init__(self, cafe=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if cafe:
            # Dynamically populate category choices
            categories = MenuCategory.objects.filter(cafe=cafe, is_active=True)
            self.fields['category'].choices = [('all', 'All Categories')] + [
                (cat.id, cat.name) for cat in categories
            ]


class DateFilterForm(forms.Form):
    """Form for filtering by date range"""
    
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Select Date'
    )
    
    date_range = forms.ChoiceField(
        required=False,
        choices=[
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('week', 'This Week'),
            ('month', 'This Month'),
            ('custom', 'Custom Date'),
        ],
        initial='today',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit()'
        }),
        label='Quick Select'
    )


class OrderStatusUpdateForm(forms.Form):
    """Form for updating order status"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Update Status'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add notes (optional)...'
        }),
        label='Notes'
    )
