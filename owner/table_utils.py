from django.utils import timezone
from .models import Table
import uuid

def auto_cleanup_tables():
    """Run periodic cleanup of table statuses"""
    tables = Table.objects.all()
    updated_count = 0
    
    for table in tables:
        if table.auto_update_status():
            updated_count += 1
    
    return {
        'success': True,
        'updated_count': updated_count,
        'message': f'✅ {updated_count} table(s) automatically cleaned up!'
    }

def scan_qr_code(table_id):
    """Handle QR code scan - Auto-update to Occupied"""
    try:
        table = Table.objects.get(id=table_id)
        
        if table.status == 'available':
            session_id = str(uuid.uuid4())
            table.occupy_table(session_id)
            return {
                'success': True,
                'table': table,
                'session_id': session_id,
                'message': f'Welcome to Table {table.table_number}!'
            }
        else:
            return {
                'success': False,
                'message': f'Table {table.table_number} is currently {table.get_status_display()}'
            }
    except Table.DoesNotExist:
        return {'success': False, 'message': 'Invalid table'}

def place_order(table_id, order_data):
    """Handle order placement - Update to In Service"""
    try:
        table = Table.objects.get(id=table_id)
        table.status = 'in_service'
        table.save()
        return {'success': True, 'message': 'Order placed!'}
    except Table.DoesNotExist:
        return {'success': False, 'message': 'Table not found'}

def request_bill(table_id):
    """Handle bill request - Update to Billing"""
    try:
        table = Table.objects.get(id=table_id)
        table.status = 'billing'
        table.save()
        return {'success': True, 'message': 'Bill requested'}
    except Table.DoesNotExist:
        return {'success': False, 'message': 'Table not found'}

def complete_payment(table_id):
    """Handle payment completion - Update to Cleaning"""
    try:
        table = Table.objects.get(id=table_id)
        table.status = 'cleaning'
        table.save()
        return {'success': True, 'message': 'Payment completed'}
    except Table.DoesNotExist:
        return {'success': False, 'message': 'Table not found'}
