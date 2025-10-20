from django.db.models import Sum, Count, Avg, F
from django.utils import timezone
from datetime import timedelta, datetime
from owner.models import Order, OrderItem, Table


def get_daily_stats(cafe, date=None):
    """Get comprehensive daily statistics"""
    if date is None:
        date = timezone.now().date()
    
    orders = Order.objects.filter(cafe=cafe, created_at__date=date)
    
    total_sales = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = orders.count()
    avg_order = total_sales / total_orders if total_orders > 0 else 0
    
    completed_orders = orders.filter(status='completed').count()
    pending_orders = orders.filter(status__in=['pending', 'preparing']).count()
    cancelled_orders = orders.filter(status='cancelled').count()
    
    return {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'avg_order_value': avg_order,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'cancelled_orders': cancelled_orders,
        'date': date,
    }


def get_top_selling_items(cafe, date=None, limit=5):
    """Get top selling menu items"""
    if date is None:
        date = timezone.now().date()
    
    items = OrderItem.objects.filter(
        order__cafe=cafe,
        order__created_at__date=date,
        order__status__in=['completed', 'preparing', 'pending']
    ).values(
        'menu_item__name', 'menu_item__id'
    ).annotate(
        quantity=Sum('quantity'),
        revenue=Sum('subtotal')
    ).order_by('-quantity')[:limit]
    
    return items


def get_order_status_breakdown(cafe, date=None):
    """Get breakdown of orders by status"""
    if date is None:
        date = timezone.now().date()
    
    breakdown = Order.objects.filter(
        cafe=cafe,
        created_at__date=date
    ).values('status').annotate(
        count=Count('id'),
        total_revenue=Sum('total_amount')
    ).order_by('-count')
    
    return breakdown


def get_table_statistics(cafe):
    """Get table occupancy statistics"""
    tables = Table.objects.filter(cafe=cafe)
    
    total = tables.count()
    available = tables.filter(status='available').count()
    occupied = tables.filter(status='occupied').count()
    reserved = tables.filter(status='reserved').count()
    cleaning = tables.filter(status='cleaning').count() if hasattr(Table, 'STATUS_CHOICES') else 0
    
    occupancy_rate = (occupied / total * 100) if total > 0 else 0
    
    return {
        'total': total,
        'available': available,
        'occupied': occupied,
        'reserved': reserved,
        'cleaning': cleaning,
        'occupancy_rate': round(occupancy_rate, 1),
    }


def get_hourly_sales(cafe, date=None):
    """Get hourly sales breakdown"""
    if date is None:
        date = timezone.now().date()
    
    from django.db.models.functions import ExtractHour
    
    hourly_data = Order.objects.filter(
        cafe=cafe,
        created_at__date=date,
        status__in=['completed', 'pending', 'preparing']
    ).annotate(
        hour=ExtractHour('created_at')
    ).values('hour').annotate(
        orders_count=Count('id'),
        total_sales=Sum('total_amount')
    ).order_by('hour')
    
    # Fill missing hours with zero
    result = []
    for hour in range(24):
        hour_data = next((item for item in hourly_data if item['hour'] == hour), None)
        if hour_data:
            result.append({
                'hour': hour,
                'orders': hour_data['orders_count'],
                'sales': float(hour_data['total_sales'] or 0)
            })
        else:
            result.append({'hour': hour, 'orders': 0, 'sales': 0})
    
    return result


def calculate_revenue_metrics(cafe, start_date=None, end_date=None):
    """Calculate comprehensive revenue metrics"""
    if start_date is None:
        start_date = timezone.now().date()
    if end_date is None:
        end_date = start_date
    
    orders = Order.objects.filter(
        cafe=cafe,
        created_at__date__range=[start_date, end_date],
        status='completed'
    )
    
    metrics = orders.aggregate(
        total_revenue=Sum('total_amount'),
        total_orders=Count('id'),
        avg_order_value=Avg('total_amount')
    )
    
    return {
        'total_revenue': metrics['total_revenue'] or 0,
        'total_orders': metrics['total_orders'] or 0,
        'avg_order_value': metrics['avg_order_value'] or 0,
        'start_date': start_date,
        'end_date': end_date,
    }


def get_weekly_comparison(cafe):
    """Get week-over-week comparison"""
    today = timezone.now().date()
    
    # This week
    week_start = today - timedelta(days=today.weekday())
    this_week = Order.objects.filter(
        cafe=cafe,
        created_at__date__gte=week_start,
        status='completed'
    ).aggregate(
        revenue=Sum('total_amount'),
        orders=Count('id')
    )
    
    # Last week
    last_week_start = week_start - timedelta(days=7)
    last_week_end = week_start - timedelta(days=1)
    last_week = Order.objects.filter(
        cafe=cafe,
        created_at__date__range=[last_week_start, last_week_end],
        status='completed'
    ).aggregate(
        revenue=Sum('total_amount'),
        orders=Count('id')
    )
    
    # Calculate growth
    revenue_growth = 0
    orders_growth = 0
    
    if last_week['revenue']:
        revenue_growth = ((this_week['revenue'] or 0) - last_week['revenue']) / last_week['revenue'] * 100
    
    if last_week['orders']:
        orders_growth = ((this_week['orders'] or 0) - last_week['orders']) / last_week['orders'] * 100
    
    return {
        'this_week': this_week,
        'last_week': last_week,
        'revenue_growth': round(revenue_growth, 1),
        'orders_growth': round(orders_growth, 1),
    }
