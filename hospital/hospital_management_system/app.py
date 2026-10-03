from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime, timedelta
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from functools import wraps
import json
from sqlalchemy import inspect, text, func, distinct

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'hospital_management_secret_key_2024'
app.config['UPLOAD_FOLDER'] = 'static/images/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)

# ==================== DATABASE MODELS ====================

class HospitalInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default='MediCare Hospital')
    description = db.Column(db.Text, default='Providing world-class healthcare services')
    established_year = db.Column(db.Integer, default=2020)
    phone = db.Column(db.String(20), default='+1-800-HOSPITAL')
    email = db.Column(db.String(100), default='info@hospital.com')
    address = db.Column(db.String(200), default='123 Medical Plaza, Healthcare City')
    website = db.Column(db.String(100), default='www.hospital.com')
    rating = db.Column(db.Float, default=4.8)
    total_beds = db.Column(db.Integer, default=200)
    emergency_number = db.Column(db.String(20), default='911')

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    experience = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    image = db.Column(db.String(255))
    availability = db.Column(db.String(50), default='Available')
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    department = db.relationship('Department', foreign_keys=[department_id], backref='doctors')

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    head_doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    status = db.Column(db.String(20), nullable=False, default='Active')
    created_at = db.Column(db.DateTime, default=datetime.now)
    head_doctor = db.relationship('Doctor', foreign_keys=[head_doctor_id])

class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    charge = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Bed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bed_number = db.Column(db.String(50), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    ward = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Available')
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    patient = db.relationship('User', backref='beds')

class LabTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requested_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    test_name = db.Column(db.String(150), nullable=False)
    test_type = db.Column(db.String(100), nullable=False)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Pending')
    result = db.Column(db.Text)
    reference_range = db.Column(db.String(255))
    notes = db.Column(db.Text)
    sample_collected_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    patient = db.relationship('User', foreign_keys=[patient_id], backref='lab_tests')
    requested_by = db.relationship('User', foreign_keys=[requested_by_id])

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    patient_name = db.Column(db.String(100), nullable=False)
    patient_email = db.Column(db.String(100), nullable=False)
    patient_phone = db.Column(db.String(20), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending')
    token_number = db.Column(db.Integer)
    queue_date = db.Column(db.Date)
    queue_status = db.Column(db.String(30), default='Waiting')
    called_at = db.Column(db.DateTime)
    consultation_started_at = db.Column(db.DateTime)
    queue_completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    doctor = db.relationship('Doctor', backref='appointments')

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    patient_name = db.Column(db.String(100), nullable=False)
    patient_email = db.Column(db.String(100), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'))
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.now)
    due_date = db.Column(db.DateTime)
    invoice_number = db.Column(db.String(40), index=True)
    discount_amount = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    payment_date = db.Column(db.DateTime)
    service = db.relationship('Service', backref='bills')
    appointment = db.relationship('Appointment', backref='bills')

class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    requested_date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship('User', backref='service_requests')
    service = db.relationship('Service', backref='service_requests')

class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    diagnosis = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    patient = db.relationship('User', backref='medical_records')

class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    medicine = db.Column(db.String(150), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(100))
    duration = db.Column(db.String(100))
    diagnosis = db.Column(db.Text)
    instructions = db.Column(db.Text)
    follow_up_date = db.Column(db.Date)
    signature_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now)
    patient = db.relationship('User', backref='prescriptions')
    doctor = db.relationship('Doctor', backref='prescriptions')

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medicine_name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    manufacturer = db.Column(db.String(150), nullable=False)
    batch_number = db.Column(db.String(80), unique=True, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    purchase_price = db.Column(db.Float, nullable=False, default=0)
    selling_price = db.Column(db.Float, nullable=False, default=0)
    expiry_date = db.Column(db.Date, nullable=False)
    low_stock_threshold = db.Column(db.Integer, nullable=False, default=10)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class MedicineSale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescription.id'))
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    dispensed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sold_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    notes = db.Column(db.Text)
    medicine = db.relationship('Medicine', backref='sales')
    patient = db.relationship('User', foreign_keys=[patient_id], backref='medicine_sales')
    prescription = db.relationship('Prescription', backref='medicine_sales')
    dispensed_by = db.relationship('User', foreign_keys=[dispensed_by_id])

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship('User', backref='notifications')

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), default='patient')  # 'admin' or 'patient'
    phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    address = db.Column(db.Text)
    medical_history = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    appointments = db.relationship('Appointment', backref='user', foreign_keys='Appointment.user_id', cascade='all, delete-orphan')
    bills = db.relationship('Bill', backref='user', foreign_keys='Bill.user_id', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ==================== UTILITY FUNCTIONS ====================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'danger')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.user_type != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_api_required():
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    user = User.query.get(session['user_id'])
    if not user or user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    return None

LAB_STATUSES = {'Pending', 'Sample Collected', 'Processing', 'Completed'}
LAB_STAFF_ROLES = {'admin', 'receptionist', 'doctor', 'lab_staff'}

def lab_api_required(allowed_roles):
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    user = User.query.get(session['user_id'])
    if not user or user.user_type not in allowed_roles:
        return jsonify({'error': 'Insufficient permissions'}), 403
    return None

def lab_payload(test):
    return {
        'id': test.id,
        'patient_id': test.patient_id,
        'patient_name': test.patient.full_name if test.patient else None,
        'patient_email': test.patient.email if test.patient else None,
        'requested_by_id': test.requested_by_id,
        'requested_by': test.requested_by.full_name if test.requested_by else None,
        'test_name': test.test_name,
        'test_type': test.test_type,
        'scheduled_date': test.scheduled_date.isoformat() if test.scheduled_date else None,
        'status': test.status,
        'result': test.result,
        'reference_range': test.reference_range,
        'notes': test.notes,
        'sample_collected_at': test.sample_collected_at.isoformat() if test.sample_collected_at else None,
        'completed_at': test.completed_at.isoformat() if test.completed_at else None,
        'created_at': test.created_at.isoformat() if test.created_at else None
    }

def lab_statistics(tests):
    today = datetime.now().date()
    return {
        'total': len(tests),
        'pending': sum(test.status != 'Completed' for test in tests),
        'completed': sum(test.status == 'Completed' for test in tests),
        'today': sum(test.scheduled_date.date() == today for test in tests)
    }

PHARMACY_STAFF_ROLES = {'admin', 'pharmacist', 'receptionist'}

def pharmacy_api_required(allowed_roles=PHARMACY_STAFF_ROLES):
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    user = User.query.get(session['user_id'])
    if not user or user.user_type not in allowed_roles:
        return jsonify({'error': 'Pharmacy access required'}), 403
    return None

def medicine_payload(medicine):
    return {
        'id': medicine.id,
        'medicine_name': medicine.medicine_name,
        'category': medicine.category,
        'manufacturer': medicine.manufacturer,
        'batch_number': medicine.batch_number,
        'quantity': medicine.quantity,
        'purchase_price': medicine.purchase_price,
        'selling_price': medicine.selling_price,
        'expiry_date': medicine.expiry_date.isoformat() if medicine.expiry_date else None,
        'low_stock_threshold': medicine.low_stock_threshold,
        'is_low_stock': medicine.quantity <= medicine.low_stock_threshold,
        'is_expiring_soon': medicine.expiry_date <= date.today() + timedelta(days=30),
        'is_expired': medicine.expiry_date < date.today()
    }

def medicine_sale_payload(sale):
    return {
        'id': sale.id,
        'medicine_id': sale.medicine_id,
        'medicine_name': sale.medicine.medicine_name,
        'batch_number': sale.medicine.batch_number,
        'patient_id': sale.patient_id,
        'patient_name': sale.patient.full_name,
        'prescription_id': sale.prescription_id,
        'quantity': sale.quantity,
        'unit_price': sale.unit_price,
        'total_amount': sale.total_amount,
        'dispensed_by': sale.dispensed_by.full_name,
        'sold_at': sale.sold_at.isoformat(),
        'notes': sale.notes
    }

def pharmacy_statistics(medicines, sales):
    today = date.today()
    expiry_cutoff = today + timedelta(days=30)
    return {
        'total_medicines': len(medicines),
        'low_stock': sum(item.quantity <= item.low_stock_threshold for item in medicines),
        'expiring_soon': sum(today <= item.expiry_date <= expiry_cutoff for item in medicines),
        'todays_sales': sum(sale.sold_at.date() == today for sale in sales),
        'todays_sales_amount': round(sum(sale.total_amount for sale in sales if sale.sold_at.date() == today), 2)
    }

DEPARTMENT_STATUSES = {'Active', 'Inactive'}

def department_payload(department, include_appointments=True):
    doctors = sorted(department.doctors, key=lambda doctor: doctor.name.lower())
    appointments = []
    if include_appointments:
        appointments = Appointment.query.join(Doctor).filter(Doctor.department_id == department.id).order_by(Appointment.appointment_date.desc()).all()
    return {
        'id': department.id,
        'name': department.name,
        'description': department.description,
        'head_doctor_id': department.head_doctor_id,
        'head_doctor': department.head_doctor.name if department.head_doctor else None,
        'phone': department.phone,
        'email': department.email,
        'status': department.status,
        'doctors': [{'id': doctor.id, 'name': doctor.name, 'specialization': doctor.specialization} for doctor in doctors],
        'doctor_count': len(doctors),
        'appointment_count': len(appointments),
        'appointments': [{
            'id': appointment.id,
            'patient_name': appointment.patient_name,
            'doctor_name': appointment.doctor.name,
            'appointment_date': appointment.appointment_date.isoformat(),
            'status': appointment.status,
            'reason': appointment.reason
        } for appointment in appointments]
    }

def department_statistics(departments):
    department_ids = [department.id for department in departments]
    assigned_doctors = Doctor.query.filter(Doctor.department_id.in_(department_ids)).count() if department_ids else 0
    appointments = Appointment.query.join(Doctor).filter(Doctor.department_id.in_(department_ids)).count() if department_ids else 0
    return {
        'total_departments': len(departments),
        'active_departments': sum(department.status == 'Active' for department in departments),
        'assigned_doctors': assigned_doctors,
        'appointments': appointments
    }

QUEUE_STATUSES = {'Waiting', 'Called', 'In Consultation', 'Completed', 'No Show'}
ACTIVE_QUEUE_STATUSES = {'Waiting', 'Called', 'In Consultation'}
QUEUE_STAFF_ROLES = {'admin', 'receptionist', 'doctor'}

def queue_payload(appointment):
    return {
        'id': appointment.id,
        'token_number': appointment.token_number,
        'queue_date': appointment.queue_date.isoformat() if appointment.queue_date else None,
        'queue_status': appointment.queue_status or 'Waiting',
        'patient_name': appointment.patient_name,
        'patient_email': appointment.patient_email,
        'patient_phone': appointment.patient_phone,
        'doctor_id': appointment.doctor_id,
        'doctor_name': appointment.doctor.name,
        'department_id': appointment.doctor.department_id,
        'department_name': appointment.doctor.department.name if appointment.doctor.department else None,
        'appointment_date': appointment.appointment_date.isoformat(),
        'reason': appointment.reason,
        'called_at': appointment.called_at.isoformat() if appointment.called_at else None,
        'consultation_started_at': appointment.consultation_started_at.isoformat() if appointment.consultation_started_at else None,
        'completed_at': appointment.queue_completed_at.isoformat() if appointment.queue_completed_at else None
    }

def next_queue_token(doctor_id, queue_date):
    latest = db.session.query(db.func.max(Appointment.token_number)).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.queue_date == queue_date
    ).scalar()
    return (latest or 0) + 1

def active_queue_duplicate(patient_email, user_id, doctor_id, appointment_date, exclude_id=None):
    query = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.queue_status.in_(ACTIVE_QUEUE_STATUSES)
    )
    if exclude_id:
        query = query.filter(Appointment.id != exclude_id)
    if user_id:
        query = query.filter(db.or_(Appointment.user_id == user_id, Appointment.patient_email == patient_email))
    else:
        query = query.filter(Appointment.patient_email == patient_email)
    return query.first()

def queue_statistics(entries):
    current = next((entry for entry in entries if entry.queue_status == 'In Consultation'), None)
    current = current or next((entry for entry in entries if entry.queue_status == 'Called'), None)
    waiting = [entry for entry in entries if entry.queue_status == 'Waiting']
    completed = [entry for entry in entries if entry.queue_status == 'Completed']
    return {
        'current_token': current.token_number if current else None,
        'next_token': min((entry.token_number for entry in waiting), default=None),
        'waiting_patients': len(waiting),
        'completed_patients': len(completed)
    }

BED_STATUSES = {'Available', 'Occupied', 'Reserved', 'Maintenance'}

def bed_payload(bed):
    return {
        'id': bed.id,
        'bed_number': bed.bed_number,
        'department': bed.department,
        'ward': bed.ward,
        'status': bed.status,
        'patient_id': bed.patient_id,
        'patient_name': bed.patient.full_name if bed.patient else None,
        'assigned_at': bed.assigned_at.isoformat() if bed.assigned_at else None,
        'notes': bed.notes,
        'created_at': bed.created_at.isoformat() if bed.created_at else None
    }

def bed_statistics(beds=None):
    beds = beds if beds is not None else Bed.query.all()
    return {
        'total': len(beds),
        'available': sum(bed.status == 'Available' for bed in beds),
        'occupied': sum(bed.status == 'Occupied' for bed in beds),
        'reserved': sum(bed.status == 'Reserved' for bed in beds),
        'maintenance': sum(bed.status == 'Maintenance' for bed in beds)
    }

# ==================== ROUTES ====================

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        
        if not all([username, email, password, confirm_password, full_name]):
            flash('All fields are required', 'danger')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email, full_name=full_name, user_type='patient')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_type'] = user.user_type
            flash(f'Welcome back, {user.full_name}!', 'success')
            
            if user.user_type == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html', admin_login=False)

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, user_type='admin').first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_type'] = user.user_type
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('admin_dashboard'))

        flash('Invalid admin credentials', 'danger')

    return render_template('login.html', admin_login=True)

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        current = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirmation = request.form.get('confirm_password')
        if not user.check_password(current or ''):
            flash('Current password is incorrect', 'danger')
        elif len(new_password or '') < 6 or new_password != confirmation:
            flash('New passwords must match and contain at least 6 characters', 'danger')
        else:
            user.set_password(new_password)
            db.session.commit()
            flash('Password changed successfully', 'success')
            return redirect(url_for('user_dashboard' if user.user_type == 'patient' else 'admin_dashboard'))
    return render_template('change_password.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    reset_link = None
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user:
            serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
            token = serializer.dumps(user.id, salt='password-reset')
            reset_link = url_for('reset_password', token=token, _external=True)
        else:
            flash('If that email exists, a reset link has been generated.', 'info')
    return render_template('forgot_password.html', reset_link=reset_link)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        user_id = serializer.loads(token, salt='password-reset', max_age=1800)
    except (BadSignature, SignatureExpired):
        flash('This password reset link is invalid or expired.', 'danger')
        return redirect(url_for('forgot_password'))
    user = User.query.get(user_id)
    if request.method == 'POST':
        password = request.form.get('password')
        if len(password or '') < 6 or password != request.form.get('confirm_password'):
            flash('Passwords must match and contain at least 6 characters', 'danger')
        else:
            user.set_password(password)
            db.session.commit()
            flash('Password reset successfully. Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('reset_password.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/user-dashboard')
@login_required
def user_dashboard():
    user = User.query.get(session['user_id'])
    if user.user_type != 'patient':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    appointments = Appointment.query.filter_by(user_id=user.id).all()
    bills = Bill.query.filter_by(user_id=user.id).all()
    service_requests = ServiceRequest.query.filter_by(user_id=user.id).order_by(ServiceRequest.created_at.desc()).all()
    medical_records = MedicalRecord.query.filter_by(patient_id=user.id).order_by(MedicalRecord.created_at.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=user.id).order_by(Prescription.created_at.desc()).all()
    
    return render_template('user_dashboard.html', user=user, appointments=appointments, bills=bills, service_requests=service_requests, medical_records=medical_records, prescriptions=prescriptions)

@app.route('/admin-dashboard')
@admin_required
def admin_dashboard():
    total_users = User.query.filter_by(user_type='patient').count()
    total_appointments = Appointment.query.count()
    total_bills = Bill.query.count()
    pending_appointments = Appointment.query.filter_by(status='Pending').count()
    
    users = User.query.filter_by(user_type='patient').all()
    appointments = Appointment.query.all()
    bills = Bill.query.all()
    service_requests = ServiceRequest.query.order_by(ServiceRequest.created_at.desc()).all()
    
    return render_template('admin_dashboard.html',
                         total_users=total_users,
                         total_appointments=total_appointments,
                         total_bills=total_bills,
                         pending_appointments=pending_appointments,
                         users=users,
                         appointments=appointments,
                         bills=bills,
                         service_requests=service_requests)

@app.route('/api/users', methods=['GET'])
@admin_required
def api_users():
    users = User.query.filter_by(user_type='patient').all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'full_name': u.full_name,
        'phone': u.phone,
        'created_at': u.created_at.isoformat()
    } for u in users])

@app.route('/api/user-profile', methods=['GET', 'PUT'])
@login_required
def api_user_profile():
    user = User.query.get(session['user_id'])
    
    if request.method == 'GET':
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'phone': user.phone,
            'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
            'address': user.address,
            'medical_history': user.medical_history
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        user.full_name = data.get('full_name', user.full_name)
        user.phone = data.get('phone', user.phone)
        user.address = data.get('address', user.address)
        user.medical_history = data.get('medical_history', user.medical_history)
        
        if data.get('date_of_birth'):
            from datetime import datetime as dt
            user.date_of_birth = dt.fromisoformat(data.get('date_of_birth')).date()
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated successfully'})

# ==================== MAIN ROUTES ====================


@app.route('/')
def index():
    hospital = HospitalInfo.query.first()
    doctors_count = Doctor.query.count()
    staff_count = Staff.query.count()
    services_count = Service.query.count()
    appointments_count = Appointment.query.count()
    
    return render_template('index.html', 
                         hospital=hospital,
                         doctors_count=doctors_count,
                         staff_count=staff_count,
                         services_count=services_count,
                         appointments_count=appointments_count)

@app.route('/hospital-info')
def hospital_info():
    hospital = HospitalInfo.query.first()
    if not hospital:
        hospital = HospitalInfo()
        db.session.add(hospital)
        db.session.commit()
    return render_template('hospital_info.html', hospital=hospital)

@app.route('/api/hospital-info', methods=['GET', 'POST'])
def api_hospital_info():
    if request.method == 'POST':
        access_error = admin_api_required()
        if access_error:
            return access_error
        hospital = HospitalInfo.query.first()
        if not hospital:
            hospital = HospitalInfo()
        
        hospital.name = request.form.get('name')
        hospital.description = request.form.get('description')
        hospital.phone = request.form.get('phone')
        hospital.email = request.form.get('email')
        hospital.address = request.form.get('address')
        hospital.website = request.form.get('website')
        hospital.rating = float(request.form.get('rating', 4.8))
        hospital.total_beds = int(request.form.get('total_beds', 200))
        
        db.session.add(hospital)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Hospital info updated'})
    
    hospital = HospitalInfo.query.first()
    return jsonify({
        'id': hospital.id,
        'name': hospital.name,
        'description': hospital.description,
        'phone': hospital.phone,
        'email': hospital.email,
        'address': hospital.address,
        'website': hospital.website,
        'rating': hospital.rating,
        'total_beds': hospital.total_beds,
        'emergency_number': hospital.emergency_number
    })

# ==================== DEPARTMENTS ====================

@app.route('/departments')
def departments_page():
    departments = Department.query.order_by(Department.name).all()
    doctors = Doctor.query.order_by(Doctor.name).all()
    return render_template('departments.html', departments=departments, doctors=doctors)

@app.route('/api/departments', methods=['GET', 'POST'])
def api_departments():
    if request.method == 'POST':
        access_error = admin_api_required()
        if access_error:
            return access_error
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        status = (data.get('status') or 'Active').strip()
        if not name:
            return jsonify({'error': 'Department name is required'}), 400
        if status not in DEPARTMENT_STATUSES:
            return jsonify({'error': 'Invalid department status'}), 400
        if Department.query.filter(db.func.lower(Department.name) == name.lower()).first():
            return jsonify({'error': 'A department with this name already exists'}), 409
        head_doctor = None
        if data.get('head_doctor_id'):
            try:
                head_doctor = Doctor.query.get(int(data.get('head_doctor_id')))
            except (TypeError, ValueError):
                head_doctor = None
            if not head_doctor:
                return jsonify({'error': 'Head doctor not found'}), 404
        department = Department(
            name=name,
            description=(data.get('description') or '').strip() or None,
            head_doctor=head_doctor,
            phone=(data.get('phone') or '').strip() or None,
            email=(data.get('email') or '').strip() or None,
            status=status
        )
        db.session.add(department)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Department added successfully', 'department': department_payload(department)}), 201

    query = Department.query
    search = (request.args.get('q') or '').strip()
    status = (request.args.get('status') or '').strip()
    if search:
        query = query.filter(db.or_(Department.name.ilike(f'%{search}%'), Department.description.ilike(f'%{search}%')))
    if status in DEPARTMENT_STATUSES:
        query = query.filter_by(status=status)
    departments = query.order_by(Department.name).all()
    all_departments = Department.query.all()
    return jsonify({
        'departments': [department_payload(department) for department in departments],
        'statistics': department_statistics(all_departments),
        'doctors': [{'id': doctor.id, 'name': doctor.name, 'specialization': doctor.specialization, 'department_id': doctor.department_id} for doctor in Doctor.query.order_by(Doctor.name).all()]
    })

@app.route('/api/departments/<int:department_id>', methods=['GET', 'PUT', 'DELETE'])
def api_department_detail(department_id):
    department = Department.query.get(department_id)
    if not department:
        return jsonify({'error': 'Department not found'}), 404
    if request.method == 'GET':
        return jsonify(department_payload(department))

    access_error = admin_api_required()
    if access_error:
        return access_error
    if request.method == 'DELETE':
        if department.doctors:
            return jsonify({'error': 'Reassign doctors before deleting this department'}), 409
        if Appointment.query.join(Doctor).filter(Doctor.department_id == department.id).first():
            return jsonify({'error': 'Departments with appointments cannot be deleted'}), 409
        db.session.delete(department)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Department deleted successfully'})

    data = request.get_json(silent=True) or {}
    name = (data.get('name', department.name) or '').strip()
    status = (data.get('status', department.status) or '').strip()
    if not name:
        return jsonify({'error': 'Department name is required'}), 400
    if status not in DEPARTMENT_STATUSES:
        return jsonify({'error': 'Invalid department status'}), 400
    duplicate = Department.query.filter(db.func.lower(Department.name) == name.lower(), Department.id != department.id).first()
    if duplicate:
        return jsonify({'error': 'A department with this name already exists'}), 409
    head_doctor = None
    if data.get('head_doctor_id'):
        try:
            head_doctor = Doctor.query.get(int(data.get('head_doctor_id')))
        except (TypeError, ValueError):
            head_doctor = None
        if not head_doctor:
            return jsonify({'error': 'Head doctor not found'}), 404
    department.name = name
    department.description = (data.get('description', department.description) or '').strip() or None
    department.head_doctor = head_doctor
    department.phone = (data.get('phone', department.phone) or '').strip() or None
    department.email = (data.get('email', department.email) or '').strip() or None
    department.status = status
    db.session.commit()
    return jsonify({'success': True, 'message': 'Department updated successfully', 'department': department_payload(department)})

# ==================== DOCTORS ====================

@app.route('/doctors')
def doctors():
    doctors_list = Doctor.query.all()
    departments = Department.query.filter_by(status='Active').order_by(Department.name).all()
    return render_template('doctors.html', doctors=doctors_list, departments=departments)

@app.route('/api/doctors', methods=['GET', 'POST'])
def api_doctors():
    if request.method == 'POST':
        access_error = admin_api_required()
        if access_error:
            return access_error
        name = request.form.get('name')
        specialization = request.form.get('specialization')
        experience = request.form.get('experience')
        department_id = request.form.get('department_id') or None
        phone = request.form.get('phone')
        email = request.form.get('email')
        bio = request.form.get('bio')
        
        image = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"doctor_{datetime.now().timestamp()}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = f"uploads/{filename}"
        
        department = None
        if department_id:
            try:
                department = Department.query.get(int(department_id))
            except (TypeError, ValueError):
                department = None
            if not department:
                return jsonify({'error': 'Department not found'}), 404

        doctor = Doctor(
            name=name,
            specialization=specialization,
            department=department,
            experience=int(experience),
            phone=phone,
            email=email,
            image=image,
            bio=bio
        )
        db.session.add(doctor)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Doctor added successfully', 'id': doctor.id})
    
    doctors_list = Doctor.query.all()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'specialization': d.specialization,
        'department_id': d.department_id,
        'department_name': d.department.name if d.department else None,
        'experience': d.experience,
        'phone': d.phone,
        'email': d.email,
        'image': d.image,
        'bio': d.bio
    } for d in doctors_list])

@app.route('/api/doctors/<int:doctor_id>', methods=['GET', 'PUT', 'DELETE'])
def api_doctor_detail(doctor_id):
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        return jsonify({'error': 'Doctor not found'}), 404
    
    if request.method == 'GET':
        return jsonify({
            'id': doctor.id,
            'name': doctor.name,
            'specialization': doctor.specialization,
            'department_id': doctor.department_id,
            'department_name': doctor.department.name if doctor.department else None,
            'experience': doctor.experience,
            'phone': doctor.phone,
            'email': doctor.email,
            'image': doctor.image,
            'bio': doctor.bio
        })
    
    elif request.method == 'PUT':
        access_error = admin_api_required()
        if access_error:
            return access_error
        doctor.name = request.form.get('name', doctor.name)
        doctor.specialization = request.form.get('specialization', doctor.specialization)
        department_id = request.form.get('department_id')
        if department_id is not None:
            if department_id == '':
                doctor.department = None
            else:
                try:
                    department = Department.query.get(int(department_id))
                except (TypeError, ValueError):
                    department = None
                if not department:
                    return jsonify({'error': 'Department not found'}), 404
                doctor.department = department
        doctor.experience = int(request.form.get('experience', doctor.experience))
        doctor.phone = request.form.get('phone', doctor.phone)
        doctor.email = request.form.get('email', doctor.email)
        doctor.bio = request.form.get('bio', doctor.bio)
        
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"doctor_{datetime.now().timestamp()}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                doctor.image = f"uploads/{filename}"
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Doctor updated'})
    
    elif request.method == 'DELETE':
        access_error = admin_api_required()
        if access_error:
            return access_error
        db.session.delete(doctor)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Doctor deleted'})

# ==================== STAFF ====================

@app.route('/staff')
def staff_page():
    staff_list = Staff.query.all()
    return render_template('staff.html', staff=staff_list)

@app.route('/api/staff', methods=['GET', 'POST'])
def api_staff():
    if request.method == 'POST':
        access_error = admin_api_required()
        if access_error:
            return access_error
        name = request.form.get('name')
        position = request.form.get('position')
        department = request.form.get('department')
        phone = request.form.get('phone')
        email = request.form.get('email')

        if not all([name, position, department]):
            return jsonify({'success': False, 'message': 'Name, position, and department are required'}), 400
        
        image = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"staff_{datetime.now().timestamp()}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = f"uploads/{filename}"
        
        staff = Staff(
            name=name,
            position=position,
            department=department,
            phone=phone,
            email=email,
            image=image
        )
        db.session.add(staff)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Staff member added'})
    
    staff_list = Staff.query.all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'position': s.position,
        'department': s.department,
        'phone': s.phone,
        'email': s.email,
        'image': s.image
    } for s in staff_list])

# ==================== SERVICES ====================

@app.route('/services')
def services_page():
    services = Service.query.all()
    return render_template('services.html', services=services)

@app.route('/api/services', methods=['GET', 'POST'])
def api_services():
    if request.method == 'POST':
        access_error = admin_api_required()
        if access_error:
            return access_error
        data = request.get_json()
        service = Service(
            name=data.get('name'),
            description=data.get('description'),
            charge=float(data.get('charge')),
            category=data.get('category')
        )
        db.session.add(service)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Service added', 'id': service.id})
    
    services = Service.query.all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'description': s.description,
        'charge': s.charge,
        'category': s.category
    } for s in services])

@app.route('/api/service-requests', methods=['GET', 'POST'])
@login_required
def api_service_requests():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        if user.user_type != 'patient':
            return jsonify({'error': 'Only patients can request services'}), 403
        data = request.get_json() or {}
        service = Service.query.get(data.get('service_id'))
        requested_date = data.get('requested_date')
        if not service or not requested_date:
            return jsonify({'success': False, 'message': 'Service and requested date are required'}), 400
        try:
            requested_datetime = datetime.fromisoformat(requested_date)
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid requested date'}), 400
        if requested_datetime < datetime.now():
            return jsonify({'success': False, 'message': 'Requested date must be in the future'}), 400

        service_request = ServiceRequest(
            user_id=user.id,
            service_id=service.id,
            requested_date=requested_datetime,
            reason=data.get('reason')
        )
        db.session.add(service_request)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Service request submitted', 'id': service_request.id})

    requests = ServiceRequest.query.all() if user.user_type == 'admin' else ServiceRequest.query.filter_by(user_id=user.id).all()
    return jsonify([{
        'id': item.id,
        'service': item.service.name,
        'requested_date': item.requested_date.isoformat(),
        'reason': item.reason,
        'status': item.status
    } for item in requests])

@app.route('/api/service-requests/<int:request_id>', methods=['PUT'])
@admin_required
def update_service_request(request_id):
    service_request = ServiceRequest.query.get(request_id)
    if not service_request:
        return jsonify({'error': 'Service request not found'}), 404
    status = (request.get_json() or {}).get('status')
    if status not in {'Pending', 'Approved', 'Completed', 'Cancelled'}:
        return jsonify({'error': 'Invalid request status'}), 400
    service_request.status = status
    db.session.commit()
    return jsonify({'success': True, 'message': 'Service request updated'})

@app.route('/api/medical-records', methods=['GET', 'POST'])
@login_required
def api_medical_records():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        access_error = admin_api_required()
        if access_error:
            return access_error
        data = request.get_json() or {}
        patient_id = data.get('patient_id')
        patient = User.query.get(patient_id) if patient_id else None
        if not patient or patient.user_type != 'patient' or not data.get('title'):
            return jsonify({'error': 'Patient and record title are required'}), 400
        record = MedicalRecord(patient_id=patient.id, title=data['title'], diagnosis=data.get('diagnosis'), notes=data.get('notes'))
        db.session.add(record)
        db.session.commit()
        return jsonify({'success': True, 'id': record.id})
    records = MedicalRecord.query.all() if user.user_type == 'admin' else MedicalRecord.query.filter_by(patient_id=user.id).all()
    return jsonify([{'id': r.id, 'patient_id': r.patient_id, 'title': r.title, 'diagnosis': r.diagnosis, 'notes': r.notes, 'created_at': r.created_at.isoformat()} for r in records])

PRESCRIPTION_STAFF_ROLES = {'admin', 'doctor'}

def prescription_staff_api_required():
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    user = User.query.get(session['user_id'])
    if not user or user.user_type not in PRESCRIPTION_STAFF_ROLES:
        return jsonify({'error': 'Doctor or administrator access required'}), 403
    return None

def prescription_payload(prescription):
    return {
        'id': prescription.id,
        'patient_id': prescription.patient_id,
        'patient_name': prescription.patient.full_name,
        'doctor_id': prescription.doctor_id,
        'doctor_name': prescription.doctor.name if prescription.doctor else None,
        'medicine': prescription.medicine,
        'dosage': prescription.dosage,
        'frequency': prescription.frequency,
        'duration': prescription.duration,
        'diagnosis': prescription.diagnosis,
        'instructions': prescription.instructions,
        'follow_up_date': prescription.follow_up_date.isoformat() if prescription.follow_up_date else None,
        'signature_name': prescription.signature_name or (prescription.doctor.name if prescription.doctor else None),
        'created_at': prescription.created_at.isoformat()
    }

@app.route('/prescriptions')
@login_required
def prescriptions_page():
    user = User.query.get(session['user_id'])
    can_create = user.user_type in PRESCRIPTION_STAFF_ROLES
    if user.user_type == 'patient':
        prescriptions = Prescription.query.filter_by(patient_id=user.id).order_by(Prescription.created_at.desc()).all()
    elif user.user_type == 'doctor' and session.get('doctor_id'):
        prescriptions = Prescription.query.filter_by(doctor_id=session['doctor_id']).order_by(Prescription.created_at.desc()).all()
    else:
        prescriptions = Prescription.query.order_by(Prescription.created_at.desc()).all()
    return render_template(
        'prescriptions.html',
        prescriptions=prescriptions,
        patients=User.query.filter_by(user_type='patient').order_by(User.full_name).all() if can_create else [],
        doctors=Doctor.query.order_by(Doctor.name).all() if can_create else [],
        can_create=can_create,
        is_patient=user.user_type == 'patient'
    )

@app.route('/api/prescriptions', methods=['GET', 'POST'])
@login_required
def api_prescriptions():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        access_error = prescription_staff_api_required()
        if access_error:
            return access_error
        data = request.get_json(silent=True) or {}
        patient = User.query.filter_by(id=data.get('patient_id'), user_type='patient').first()
        doctor = Doctor.query.get(data.get('doctor_id')) if data.get('doctor_id') else None
        if not patient or not data.get('medicine') or not data.get('dosage'):
            return jsonify({'error': 'Patient, medicine, and dosage are required'}), 400
        if data.get('doctor_id') and not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        follow_up_date = None
        if data.get('follow_up_date'):
            try:
                follow_up_date = date.fromisoformat(data['follow_up_date'])
            except (TypeError, ValueError):
                return jsonify({'error': 'Follow-up date must be a valid date'}), 400
        signature_name = (data.get('signature_name') or '').strip() or (doctor.name if doctor else None)
        prescription = Prescription(
            patient_id=patient.id,
            doctor_id=doctor.id if doctor else None,
            medicine=str(data['medicine']).strip(),
            dosage=str(data['dosage']).strip(),
            frequency=data.get('frequency'),
            duration=data.get('duration'),
            diagnosis=data.get('diagnosis'),
            instructions=data.get('instructions'),
            follow_up_date=follow_up_date,
            signature_name=signature_name
        )
        db.session.add(prescription)
        db.session.commit()
        return jsonify({'success': True, 'prescription': prescription_payload(prescription)}), 201
    if user.user_type == 'patient':
        records = Prescription.query.filter_by(patient_id=user.id)
    elif user.user_type == 'doctor':
        doctor_id = request.args.get('doctor_id') or session.get('doctor_id')
        records = Prescription.query.filter_by(doctor_id=doctor_id) if doctor_id else Prescription.query.filter_by(id=-1)
    elif user.user_type == 'admin':
        records = Prescription.query
    else:
        return jsonify({'error': 'Access denied'}), 403
    return jsonify([prescription_payload(prescription) for prescription in records.order_by(Prescription.created_at.desc()).all()])

@app.route('/api/prescriptions/<int:prescription_id>/pdf')
@login_required
def prescription_pdf(prescription_id):
    prescription = Prescription.query.get(prescription_id)
    if not prescription:
        return jsonify({'error': 'Prescription not found'}), 404
    user = User.query.get(session['user_id'])
    if user.user_type not in {'admin'} and prescription.patient_id != user.id:
        return jsonify({'error': 'Access denied'}), 403
    try:
        from io import BytesIO
        from xml.sax.saxutils import escape
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return jsonify({'error': 'PDF support is not installed. Install the application requirements.'}), 503

    hospital = HospitalInfo.query.first() or HospitalInfo()
    doctor_name = prescription.doctor.name if prescription.doctor else prescription.signature_name or 'Attending Doctor'
    doctor_specialization = prescription.doctor.specialization if prescription.doctor else ''
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='HospitalName', parent=styles['Title'], fontSize=20, leading=24, textColor=colors.HexColor('#123b52'), alignment=TA_CENTER, spaceAfter=2))
    styles.add(ParagraphStyle(name='SmallMuted', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#5b6870')))
    styles.add(ParagraphStyle(name='SectionLabel', parent=styles['Heading3'], fontSize=9, leading=11, textColor=colors.HexColor('#1b6b86'), spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(name='BodySafe', parent=styles['BodyText'], fontSize=10, leading=14, textColor=colors.HexColor('#202a30')))
    safe = lambda value: escape(str(value or 'Not provided')).replace('\n', '<br/>')
    story = [Paragraph(safe(hospital.name), styles['HospitalName']), Paragraph(safe(hospital.address) + '  |  ' + safe(hospital.phone) + '  |  ' + safe(hospital.email), styles['SmallMuted']), Spacer(1, 8), Paragraph('DIGITAL PRESCRIPTION', styles['Heading2'])]
    doctor_patient = Table([
        [Paragraph('<b>Prescriber</b><br/>' + safe(doctor_name) + ('<br/>' + safe(doctor_specialization) if doctor_specialization else ''), styles['BodySafe']), Paragraph('<b>Patient</b><br/>' + safe(prescription.patient.full_name) + '<br/>' + safe(prescription.patient.email) + ('<br/>' + safe(prescription.patient.phone) if prescription.patient.phone else ''), styles['BodySafe'])],
        [Paragraph('<b>Issued</b><br/>' + prescription.created_at.strftime('%d %b %Y'), styles['BodySafe']), Paragraph('<b>Follow-up</b><br/>' + (prescription.follow_up_date.strftime('%d %b %Y') if prescription.follow_up_date else 'As advised'), styles['BodySafe'])]
    ], colWidths=[88 * mm, 88 * mm])
    doctor_patient.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f3f7f9')), ('BOX', (0, 0), (-1, -1), .5, colors.HexColor('#c9d8df')), ('INNERGRID', (0, 0), (-1, -1), .25, colors.HexColor('#dbe5e9')), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 9), ('RIGHTPADDING', (0, 0), (-1, -1), 9), ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
    story += [doctor_patient, Paragraph('Clinical information', styles['SectionLabel']), Paragraph('<b>Diagnosis:</b> ' + safe(prescription.diagnosis), styles['BodySafe']), Paragraph('Medication instructions', styles['SectionLabel'])]
    medication = Table([[Paragraph('<b>Medicine</b>', styles['BodySafe']), Paragraph('<b>Dosage</b>', styles['BodySafe']), Paragraph('<b>Frequency</b>', styles['BodySafe']), Paragraph('<b>Duration</b>', styles['BodySafe'])], [Paragraph(safe(prescription.medicine), styles['BodySafe']), Paragraph(safe(prescription.dosage), styles['BodySafe']), Paragraph(safe(prescription.frequency), styles['BodySafe']), Paragraph(safe(prescription.duration), styles['BodySafe'])]], colWidths=[55 * mm, 37 * mm, 45 * mm, 39 * mm])
    medication.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e7f1f4')), ('BOX', (0, 0), (-1, -1), .5, colors.HexColor('#c9d8df')), ('INNERGRID', (0, 0), (-1, -1), .25, colors.HexColor('#dbe5e9')), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7), ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]))
    story += [medication, Paragraph('Instructions: ' + safe(prescription.instructions), styles['BodySafe']), Spacer(1, 28), Paragraph('Digitally authorized by', styles['SmallMuted']), Paragraph('<b>' + safe(prescription.signature_name or doctor_name) + '</b>', styles['BodySafe']), Paragraph('This prescription is issued through the hospital record system. Verify patient identity before dispensing.', styles['SmallMuted'])]
    document.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=request.args.get('print') != '1', download_name=f'prescription-{prescription.id}.pdf')

@app.route('/api/notifications')
@login_required
def api_notifications():
    notifications = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.created_at.desc()).all()
    return jsonify([{'id': n.id, 'message': n.message, 'is_read': n.is_read, 'created_at': n.created_at.isoformat()} for n in notifications])

@app.route('/api/bills/<int:bill_id>/pay', methods=['POST'])
@login_required
def pay_bill(bill_id):
    bill = Bill.query.get(bill_id)
    if not bill:
        return jsonify({'error': 'Bill not found'}), 404
    if bill.user_id != session['user_id'] and session.get('user_type') != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    bill.status = 'Paid'
    bill.payment_date = bill.payment_date or datetime.now()
    db.session.add(Notification(user_id=bill.user_id, message=f'Bill #{bill.id} was paid successfully.'))
    db.session.commit()
    return jsonify({'success': True, 'message': 'Payment completed'})

@app.route('/api/services/<int:service_id>', methods=['GET', 'DELETE'])
def api_service_detail(service_id):
    service = Service.query.get(service_id)
    if not service:
        return jsonify({'error': 'Service not found'}), 404
    
    if request.method == 'DELETE':
        access_error = admin_api_required()
        if access_error:
            return access_error
        db.session.delete(service)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Service deleted'})
    
    return jsonify({
        'id': service.id,
        'name': service.name,
        'description': service.description,
        'charge': service.charge,
        'category': service.category
    })

# ==================== BED MANAGEMENT ====================

@app.route('/beds')
@admin_required
def beds_page():
    patients = User.query.filter_by(user_type='patient').order_by(User.full_name).all()
    beds = Bed.query.order_by(Bed.department, Bed.ward, Bed.bed_number).all()
    return render_template(
        'beds.html',
        patients=patients,
        beds=beds,
        bed_statuses=sorted(BED_STATUSES),
        statistics=bed_statistics(beds)
    )

@app.route('/api/beds', methods=['GET', 'POST'])
def api_beds():
    access_error = admin_api_required()
    if access_error:
        return access_error

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        bed_number = (data.get('bed_number') or '').strip()
        department = (data.get('department') or '').strip()
        ward = (data.get('ward') or '').strip()
        status = (data.get('status') or 'Available').strip()
        notes = (data.get('notes') or '').strip() or None

        if not all([bed_number, department, ward]):
            return jsonify({'error': 'Bed number, department, and ward are required'}), 400
        if status not in BED_STATUSES:
            return jsonify({'error': 'Invalid bed status'}), 400
        if Bed.query.filter_by(bed_number=bed_number).first():
            return jsonify({'error': 'A bed with this number already exists'}), 409

        patient = None
        patient_id = data.get('patient_id')
        if patient_id:
            try:
                patient = User.query.filter_by(id=int(patient_id), user_type='patient').first()
            except (TypeError, ValueError):
                patient = None
            if not patient:
                return jsonify({'error': 'A valid patient is required'}), 400
        if status == 'Occupied' and not patient:
            return jsonify({'error': 'An occupied bed must have an assigned patient'}), 400
        if status in {'Available', 'Maintenance'} and patient:
            return jsonify({'error': 'Available and maintenance beds cannot have a patient'}), 400

        bed = Bed(
            bed_number=bed_number,
            department=department,
            ward=ward,
            status=status,
            patient=patient,
            assigned_at=datetime.now() if patient else None,
            notes=notes
        )
        db.session.add(bed)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Bed added successfully', 'bed': bed_payload(bed)}), 201

    query = Bed.query
    search = (request.args.get('q') or '').strip()
    status = (request.args.get('status') or '').strip()
    department = (request.args.get('department') or '').strip()
    ward = (request.args.get('ward') or '').strip()
    if search:
        query = query.filter(db.or_(
            Bed.bed_number.ilike(f'%{search}%'),
            Bed.department.ilike(f'%{search}%'),
            Bed.ward.ilike(f'%{search}%')
        ))
    if status in BED_STATUSES:
        query = query.filter_by(status=status)
    if department:
        query = query.filter_by(department=department)
    if ward:
        query = query.filter_by(ward=ward)

    beds = query.order_by(Bed.department, Bed.ward, Bed.bed_number).all()
    all_beds = Bed.query.all()
    return jsonify({
        'beds': [bed_payload(bed) for bed in beds],
        'statistics': bed_statistics(all_beds),
        'departments': sorted({bed.department for bed in all_beds}),
        'wards': sorted({bed.ward for bed in all_beds})
    })

@app.route('/api/beds/<int:bed_id>', methods=['PUT', 'DELETE'])
def api_bed_detail(bed_id):
    access_error = admin_api_required()
    if access_error:
        return access_error
    bed = Bed.query.get(bed_id)
    if not bed:
        return jsonify({'error': 'Bed not found'}), 404

    if request.method == 'DELETE':
        if bed.status == 'Occupied' or bed.patient_id:
            return jsonify({'error': 'Release the bed before deleting it'}), 409
        db.session.delete(bed)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Bed deleted successfully'})

    data = request.get_json(silent=True) or {}
    bed_number = (data.get('bed_number', bed.bed_number) or '').strip()
    department = (data.get('department', bed.department) or '').strip()
    ward = (data.get('ward', bed.ward) or '').strip()
    status = (data.get('status', bed.status) or '').strip()
    notes = (data.get('notes', bed.notes) or '').strip() or None
    if not all([bed_number, department, ward]):
        return jsonify({'error': 'Bed number, department, and ward are required'}), 400
    if status not in BED_STATUSES:
        return jsonify({'error': 'Invalid bed status'}), 400
    duplicate = Bed.query.filter(Bed.bed_number == bed_number, Bed.id != bed.id).first()
    if duplicate:
        return jsonify({'error': 'A bed with this number already exists'}), 409
    if status == 'Occupied' and not bed.patient_id:
        return jsonify({'error': 'Assign a patient before marking the bed occupied'}), 400

    bed.bed_number = bed_number
    bed.department = department
    bed.ward = ward
    bed.status = status
    bed.notes = notes
    if status in {'Available', 'Maintenance'}:
        bed.patient_id = None
        bed.assigned_at = None
    elif status == 'Reserved':
        bed.patient_id = None
        bed.assigned_at = None
    db.session.commit()
    return jsonify({'success': True, 'message': 'Bed updated successfully', 'bed': bed_payload(bed)})

@app.route('/api/beds/<int:bed_id>/assign', methods=['POST'])
def assign_bed(bed_id):
    access_error = admin_api_required()
    if access_error:
        return access_error
    bed = Bed.query.get(bed_id)
    if not bed:
        return jsonify({'error': 'Bed not found'}), 404
    if bed.status not in {'Available', 'Reserved'} or bed.patient_id:
        return jsonify({'error': 'Only an available or reserved bed can be assigned'}), 409
    data = request.get_json(silent=True) or {}
    try:
        patient_id = int(data.get('patient_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'A valid patient is required'}), 400
    patient = User.query.filter_by(id=patient_id, user_type='patient').first()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    bed.patient_id = patient.id
    bed.status = 'Occupied'
    bed.assigned_at = datetime.now()
    db.session.add(Notification(user_id=patient.id, message=f'Bed {bed.bed_number} has been assigned to you.'))
    db.session.commit()
    return jsonify({'success': True, 'message': 'Bed assigned successfully', 'bed': bed_payload(bed)})

@app.route('/api/beds/<int:bed_id>/release', methods=['POST'])
def release_bed(bed_id):
    access_error = admin_api_required()
    if access_error:
        return access_error
    bed = Bed.query.get(bed_id)
    if not bed:
        return jsonify({'error': 'Bed not found'}), 404
    if bed.status != 'Occupied' or not bed.patient_id:
        return jsonify({'error': 'Only an occupied bed can be released'}), 409

    patient_id = bed.patient_id
    bed.patient_id = None
    bed.status = 'Available'
    bed.assigned_at = None
    db.session.add(Notification(user_id=patient_id, message=f'Bed {bed.bed_number} has been released.'))
    db.session.commit()
    return jsonify({'success': True, 'message': 'Bed released successfully', 'bed': bed_payload(bed)})

# ==================== LABORATORY MANAGEMENT ====================

@app.route('/laboratory')
@login_required
def laboratory_page():
    user = User.query.get(session['user_id'])
    is_patient = user.user_type == 'patient'
    patients = [user] if is_patient else User.query.filter_by(user_type='patient').order_by(User.full_name).all()
    return render_template(
        'laboratory.html',
        patients=patients,
        lab_statuses=sorted(LAB_STATUSES),
        can_create=user.user_type in {'admin', 'receptionist', 'patient'},
        can_request=user.user_type == 'doctor',
        can_process=user.user_type in {'admin', 'lab_staff'},
        is_patient=is_patient
    )

@app.route('/api/lab-tests', methods=['GET', 'POST'])
@login_required
def api_lab_tests():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        if user.user_type not in {'admin', 'receptionist', 'patient'}:
            return jsonify({'error': 'Only admin, reception, or patients can book lab tests'}), 403
        data = request.get_json(silent=True) or {}
        test_name = (data.get('test_name') or '').strip()
        test_type = (data.get('test_type') or '').strip()
        scheduled_value = data.get('scheduled_date')
        if not test_name or not test_type or not scheduled_value:
            return jsonify({'error': 'Test name, test type, and scheduled date are required'}), 400
        try:
            scheduled_date = datetime.fromisoformat(scheduled_value)
        except (TypeError, ValueError):
            return jsonify({'error': 'Scheduled date must be a valid date and time'}), 400
        if scheduled_date < datetime.now():
            return jsonify({'error': 'Scheduled date must be in the future'}), 400

        patient_id = user.id if user.user_type == 'patient' else data.get('patient_id')
        try:
            patient_id = int(patient_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'A valid patient is required'}), 400
        patient = User.query.filter_by(id=patient_id, user_type='patient').first()
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404

        test = LabTest(
            patient_id=patient.id,
            requested_by_id=user.id,
            test_name=test_name,
            test_type=test_type,
            scheduled_date=scheduled_date,
            reference_range=(data.get('reference_range') or '').strip() or None,
            notes=(data.get('notes') or '').strip() or None
        )
        db.session.add(test)
        db.session.add(Notification(user_id=patient.id, message=f'Lab test booked: {test_name}.'))
        db.session.commit()
        return jsonify({'success': True, 'message': 'Lab test booked successfully', 'test': lab_payload(test)}), 201

    query = LabTest.query
    if user.user_type == 'patient':
        query = query.filter_by(patient_id=user.id)
    search = (request.args.get('q') or '').strip()
    status = (request.args.get('status') or '').strip()
    patient_id = request.args.get('patient_id')
    date_value = (request.args.get('date') or '').strip()
    if search:
        query = query.join(User, LabTest.patient_id == User.id).filter(db.or_(
            LabTest.test_name.ilike(f'%{search}%'),
            LabTest.test_type.ilike(f'%{search}%'),
            LabTest.status.ilike(f'%{search}%'),
            User.full_name.ilike(f'%{search}%')
        ))
    if status in LAB_STATUSES:
        query = query.filter_by(status=status)
    if patient_id and user.user_type != 'patient':
        try:
            query = query.filter_by(patient_id=int(patient_id))
        except ValueError:
            return jsonify({'error': 'Invalid patient filter'}), 400
    if date_value:
        try:
            requested_date = datetime.fromisoformat(date_value).date()
        except ValueError:
            return jsonify({'error': 'Invalid date filter'}), 400
        start = datetime.combine(requested_date, datetime.min.time())
        end = start + timedelta(days=1)
        query = query.filter(LabTest.scheduled_date >= start, LabTest.scheduled_date < end)

    scoped_tests = LabTest.query.filter_by(patient_id=user.id).all() if user.user_type == 'patient' else LabTest.query.all()
    tests = query.order_by(LabTest.scheduled_date.desc()).all()
    return jsonify({
        'tests': [lab_payload(test) for test in tests],
        'statistics': lab_statistics(scoped_tests),
        'patients': [{'id': patient.id, 'name': patient.full_name, 'email': patient.email} for patient in User.query.filter_by(user_type='patient').order_by(User.full_name).all()] if user.user_type != 'patient' else []
    })

@app.route('/api/lab-tests/request', methods=['POST'])
@login_required
def request_lab_test():
    access_error = lab_api_required({'doctor'})
    if access_error:
        return access_error
    doctor = User.query.get(session['user_id'])
    data = request.get_json(silent=True) or {}
    try:
        patient_id = int(data.get('patient_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'A valid patient is required'}), 400
    patient = User.query.filter_by(id=patient_id, user_type='patient').first()
    test_name = (data.get('test_name') or '').strip()
    test_type = (data.get('test_type') or '').strip()
    scheduled_value = data.get('scheduled_date')
    if not patient or not test_name or not test_type or not scheduled_value:
        return jsonify({'error': 'Patient, test name, test type, and scheduled date are required'}), 400
    try:
        scheduled_date = datetime.fromisoformat(scheduled_value)
    except (TypeError, ValueError):
        return jsonify({'error': 'Scheduled date must be a valid date and time'}), 400
    if scheduled_date < datetime.now():
        return jsonify({'error': 'Scheduled date must be in the future'}), 400

    test = LabTest(
        patient_id=patient.id,
        requested_by_id=doctor.id,
        test_name=test_name,
        test_type=test_type,
        scheduled_date=scheduled_date,
        reference_range=(data.get('reference_range') or '').strip() or None,
        notes=(data.get('notes') or '').strip() or None
    )
    db.session.add(test)
    db.session.add(Notification(user_id=patient.id, message=f'Doctor requested a lab test: {test_name}.'))
    db.session.commit()
    return jsonify({'success': True, 'message': 'Lab test requested successfully', 'test': lab_payload(test)}), 201

@app.route('/api/lab-tests/<int:test_id>', methods=['GET', 'PUT'])
@login_required
def api_lab_test_detail(test_id):
    test = LabTest.query.get(test_id)
    if not test:
        return jsonify({'error': 'Lab test not found'}), 404
    user = User.query.get(session['user_id'])
    if user.user_type == 'patient' and test.patient_id != user.id:
        return jsonify({'error': 'Access denied'}), 403
    if user.user_type not in LAB_STAFF_ROLES and user.user_type != 'patient':
        return jsonify({'error': 'Access denied'}), 403

    if request.method == 'GET':
        return jsonify(lab_payload(test))
    if user.user_type not in {'admin', 'lab_staff'}:
        return jsonify({'error': 'Only lab staff or admin can update test results'}), 403

    data = request.get_json(silent=True) or {}
    status = (data.get('status', test.status) or '').strip()
    result = (data.get('result', test.result) or '').strip() or None
    reference_range = (data.get('reference_range', test.reference_range) or '').strip() or None
    notes = (data.get('notes', test.notes) or '').strip() or None
    if status not in LAB_STATUSES:
        return jsonify({'error': 'Invalid lab test status'}), 400
    if status == 'Completed' and not result:
        return jsonify({'error': 'A completed test must include results'}), 400
    test.status = status
    test.result = result
    test.reference_range = reference_range
    test.notes = notes
    if status == 'Sample Collected' and not test.sample_collected_at:
        test.sample_collected_at = datetime.now()
    if status == 'Completed':
        test.completed_at = test.completed_at or datetime.now()
        db.session.add(Notification(user_id=test.patient_id, message=f'Your lab report is ready: {test.test_name}.'))
    elif status != 'Completed':
        test.completed_at = None
    db.session.commit()
    return jsonify({'success': True, 'message': 'Lab test updated successfully', 'test': lab_payload(test)})

@app.route('/lab-tests/<int:test_id>/report')
@login_required
def lab_report(test_id):
    test = LabTest.query.get(test_id)
    if not test:
        return render_template('404.html'), 404
    user = User.query.get(session['user_id'])
    if test.status != 'Completed' or (user.user_type == 'patient' and test.patient_id != user.id) or (user.user_type not in LAB_STAFF_ROLES and user.user_type != 'patient'):
        return render_template('404.html'), 404
    return render_template('lab_report.html', test=test)

# ==================== PHARMACY MANAGEMENT ====================

@app.route('/pharmacy')
@login_required
def pharmacy_page():
    user = User.query.get(session['user_id'])
    if user.user_type not in PHARMACY_STAFF_ROLES:
        flash('Pharmacy access required', 'danger')
        return redirect(url_for('index'))
    patients = User.query.filter_by(user_type='patient').order_by(User.full_name).all()
    return render_template(
        'pharmacy.html',
        patients=patients,
        can_delete=user.user_type in {'admin', 'pharmacist'},
        can_adjust_stock=user.user_type in {'admin', 'pharmacist'}
    )

@app.route('/api/medicines', methods=['GET', 'POST'])
def api_medicines():
    access_error = pharmacy_api_required()
    if access_error:
        return access_error
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        medicine_name = (data.get('medicine_name') or '').strip()
        category = (data.get('category') or '').strip()
        manufacturer = (data.get('manufacturer') or '').strip()
        batch_number = (data.get('batch_number') or '').strip()
        if not all([medicine_name, category, manufacturer, batch_number, data.get('expiry_date')]):
            return jsonify({'error': 'Medicine name, category, manufacturer, batch number, and expiry date are required'}), 400
        try:
            quantity = int(data.get('quantity', 0))
            purchase_price = float(data.get('purchase_price', 0))
            selling_price = float(data.get('selling_price', 0))
            low_stock_threshold = int(data.get('low_stock_threshold', 10))
            expiry_date = date.fromisoformat(data.get('expiry_date'))
        except (TypeError, ValueError):
            return jsonify({'error': 'Quantity, prices, threshold, and expiry date must be valid values'}), 400
        if min(quantity, purchase_price, selling_price, low_stock_threshold) < 0:
            return jsonify({'error': 'Quantity, prices, and low-stock threshold cannot be negative'}), 400
        if expiry_date < date.today():
            return jsonify({'error': 'Expiry date cannot be in the past'}), 400
        if Medicine.query.filter_by(batch_number=batch_number).first():
            return jsonify({'error': 'A medicine with this batch number already exists'}), 409

        medicine = Medicine(
            medicine_name=medicine_name,
            category=category,
            manufacturer=manufacturer,
            batch_number=batch_number,
            quantity=quantity,
            purchase_price=purchase_price,
            selling_price=selling_price,
            expiry_date=expiry_date,
            low_stock_threshold=low_stock_threshold
        )
        db.session.add(medicine)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Medicine added successfully', 'medicine': medicine_payload(medicine)}), 201

    query = Medicine.query
    search = (request.args.get('q') or '').strip()
    category = (request.args.get('category') or '').strip()
    if search:
        query = query.filter(db.or_(
            Medicine.medicine_name.ilike(f'%{search}%'),
            Medicine.category.ilike(f'%{search}%'),
            Medicine.manufacturer.ilike(f'%{search}%'),
            Medicine.batch_number.ilike(f'%{search}%')
        ))
    if category:
        query = query.filter_by(category=category)
    if request.args.get('low_stock') == '1':
        query = query.filter(Medicine.quantity <= Medicine.low_stock_threshold)
    if request.args.get('expiring') == '1':
        query = query.filter(Medicine.expiry_date >= date.today(), Medicine.expiry_date <= date.today() + timedelta(days=30))
    medicines = query.order_by(Medicine.expiry_date, Medicine.medicine_name).all()
    all_medicines = Medicine.query.all()
    sales = MedicineSale.query.all()
    return jsonify({
        'medicines': [medicine_payload(medicine) for medicine in medicines],
        'statistics': pharmacy_statistics(all_medicines, sales),
        'categories': sorted({medicine.category for medicine in all_medicines})
    })

@app.route('/api/medicines/<int:medicine_id>', methods=['PUT', 'DELETE'])
def api_medicine_detail(medicine_id):
    access_error = pharmacy_api_required()
    if access_error:
        return access_error
    medicine = Medicine.query.get(medicine_id)
    if not medicine:
        return jsonify({'error': 'Medicine not found'}), 404
    user = User.query.get(session['user_id'])

    if request.method == 'DELETE':
        if user.user_type not in {'admin', 'pharmacist'}:
            return jsonify({'error': 'Only admin or pharmacist can delete medicines'}), 403
        if MedicineSale.query.filter_by(medicine_id=medicine.id).first():
            return jsonify({'error': 'Medicines with dispensing history cannot be deleted'}), 409
        db.session.delete(medicine)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Medicine deleted successfully'})

    data = request.get_json(silent=True) or {}
    medicine_name = (data.get('medicine_name', medicine.medicine_name) or '').strip()
    category = (data.get('category', medicine.category) or '').strip()
    manufacturer = (data.get('manufacturer', medicine.manufacturer) or '').strip()
    batch_number = (data.get('batch_number', medicine.batch_number) or '').strip()
    if not all([medicine_name, category, manufacturer, batch_number, data.get('expiry_date', medicine.expiry_date.isoformat())]):
        return jsonify({'error': 'Medicine name, category, manufacturer, batch number, and expiry date are required'}), 400
    try:
        quantity = int(data.get('quantity', medicine.quantity))
        purchase_price = float(data.get('purchase_price', medicine.purchase_price))
        selling_price = float(data.get('selling_price', medicine.selling_price))
        low_stock_threshold = int(data.get('low_stock_threshold', medicine.low_stock_threshold))
        expiry_date = date.fromisoformat(data.get('expiry_date', medicine.expiry_date.isoformat()))
    except (TypeError, ValueError):
        return jsonify({'error': 'Quantity, prices, threshold, and expiry date must be valid values'}), 400
    if min(quantity, purchase_price, selling_price, low_stock_threshold) < 0:
        return jsonify({'error': 'Quantity, prices, and low-stock threshold cannot be negative'}), 400
    if expiry_date < date.today():
        return jsonify({'error': 'Expiry date cannot be in the past'}), 400
    duplicate = Medicine.query.filter(Medicine.batch_number == batch_number, Medicine.id != medicine.id).first()
    if duplicate:
        return jsonify({'error': 'A medicine with this batch number already exists'}), 409

    medicine.medicine_name = medicine_name
    medicine.category = category
    medicine.manufacturer = manufacturer
    medicine.batch_number = batch_number
    medicine.quantity = quantity
    medicine.purchase_price = purchase_price
    medicine.selling_price = selling_price
    medicine.expiry_date = expiry_date
    medicine.low_stock_threshold = low_stock_threshold
    db.session.commit()
    return jsonify({'success': True, 'message': 'Medicine updated successfully', 'medicine': medicine_payload(medicine)})

@app.route('/api/medicines/<int:medicine_id>/stock', methods=['POST'])
def update_medicine_stock(medicine_id):
    access_error = pharmacy_api_required({'admin', 'pharmacist'})
    if access_error:
        return access_error
    medicine = Medicine.query.get(medicine_id)
    if not medicine:
        return jsonify({'error': 'Medicine not found'}), 404
    data = request.get_json(silent=True) or {}
    try:
        change = int(data.get('change'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Stock change must be a non-zero whole number'}), 400
    if change == 0:
        return jsonify({'error': 'Stock change must be a non-zero whole number'}), 400
    if medicine.quantity + change < 0:
        return jsonify({'error': 'Stock cannot be reduced below zero'}), 400
    medicine.quantity += change
    db.session.commit()
    return jsonify({'success': True, 'message': 'Stock updated successfully', 'medicine': medicine_payload(medicine)})

@app.route('/api/pharmacy/patients/<int:patient_id>/prescriptions')
def patient_prescriptions_for_pharmacy(patient_id):
    access_error = pharmacy_api_required()
    if access_error:
        return access_error
    patient = User.query.filter_by(id=patient_id, user_type='patient').first()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).order_by(Prescription.created_at.desc()).all()
    return jsonify([{
        'id': prescription.id,
        'medicine': prescription.medicine,
        'dosage': prescription.dosage,
        'instructions': prescription.instructions,
        'created_at': prescription.created_at.isoformat()
    } for prescription in prescriptions])

@app.route('/api/medicine-sales', methods=['GET', 'POST'])
def api_medicine_sales():
    access_error = pharmacy_api_required()
    if access_error:
        return access_error
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        try:
            medicine_id = int(data.get('medicine_id'))
            patient_id = int(data.get('patient_id'))
            quantity = int(data.get('quantity'))
        except (TypeError, ValueError):
            return jsonify({'error': 'Medicine, patient, and quantity are required'}), 400
        if quantity <= 0:
            return jsonify({'error': 'Quantity must be greater than zero'}), 400
        medicine = Medicine.query.get(medicine_id)
        patient = User.query.filter_by(id=patient_id, user_type='patient').first()
        if not medicine or not patient:
            return jsonify({'error': 'Medicine or patient not found'}), 404
        if medicine.expiry_date < date.today():
            return jsonify({'error': 'Expired medicine cannot be dispensed'}), 400
        if quantity > medicine.quantity:
            return jsonify({'error': 'Insufficient stock'}), 400

        prescription = None
        prescription_id = data.get('prescription_id')
        if prescription_id:
            try:
                prescription = Prescription.query.filter_by(id=int(prescription_id), patient_id=patient.id).first()
            except (TypeError, ValueError):
                prescription = None
            if not prescription or prescription.medicine.strip().lower() != medicine.medicine_name.strip().lower():
                return jsonify({'error': 'Selected prescription does not match this medicine and patient'}), 400
        else:
            prescription = Prescription.query.filter(
                Prescription.patient_id == patient.id,
                db.func.lower(Prescription.medicine) == medicine.medicine_name.strip().lower()
            ).order_by(Prescription.created_at.desc()).first()

        sale = MedicineSale(
            medicine_id=medicine.id,
            patient_id=patient.id,
            prescription_id=prescription.id if prescription else None,
            quantity=quantity,
            unit_price=medicine.selling_price,
            total_amount=round(medicine.selling_price * quantity, 2),
            dispensed_by_id=user.id,
            notes=(data.get('notes') or '').strip() or None
        )
        medicine.quantity -= quantity
        db.session.add(sale)
        db.session.add(Notification(user_id=patient.id, message=f'{quantity} unit(s) of {medicine.medicine_name} were dispensed.'))
        db.session.commit()
        return jsonify({'success': True, 'message': 'Medicine dispensed successfully', 'sale': medicine_sale_payload(sale)}), 201

    query = MedicineSale.query
    search = (request.args.get('q') or '').strip()
    if search:
        query = query.join(Medicine).join(User, MedicineSale.patient_id == User.id).filter(db.or_(
            Medicine.medicine_name.ilike(f'%{search}%'),
            Medicine.batch_number.ilike(f'%{search}%'),
            User.full_name.ilike(f'%{search}%')
        ))
    sales = query.order_by(MedicineSale.sold_at.desc()).all()
    return jsonify([medicine_sale_payload(sale) for sale in sales])

@app.route('/api/my-medicine-sales')
@login_required
def my_medicine_sales():
    sales = MedicineSale.query.filter_by(patient_id=session['user_id']).order_by(MedicineSale.sold_at.desc()).all()
    return jsonify([medicine_sale_payload(sale) for sale in sales])

# ==================== TOKEN QUEUE MANAGEMENT ====================

@app.route('/queue')
def queue_page():
    return render_template(
        'queue.html',
        doctors=Doctor.query.order_by(Doctor.name).all(),
        departments=Department.query.filter_by(status='Active').order_by(Department.name).all(),
        queue_statuses=sorted(QUEUE_STATUSES),
        can_manage=session.get('user_type') in QUEUE_STAFF_ROLES
    )

@app.route('/api/queue', methods=['GET'])
def api_queue():
    queue_date_value = request.args.get('date') or date.today().isoformat()
    try:
        queue_date = date.fromisoformat(queue_date_value)
    except ValueError:
        return jsonify({'error': 'Invalid queue date'}), 400
    query = Appointment.query.join(Doctor).filter(Appointment.queue_date == queue_date)
    doctor_id = request.args.get('doctor_id')
    department_id = request.args.get('department_id')
    status = request.args.get('status')
    if doctor_id:
        try:
            query = query.filter(Appointment.doctor_id == int(doctor_id))
        except ValueError:
            return jsonify({'error': 'Invalid doctor filter'}), 400
    if department_id:
        try:
            query = query.filter(Doctor.department_id == int(department_id))
        except ValueError:
            return jsonify({'error': 'Invalid department filter'}), 400
    if status in QUEUE_STATUSES:
        query = query.filter(Appointment.queue_status == status)
    entries = query.order_by(Appointment.token_number, Appointment.appointment_date).all()
    return jsonify({
        'date': queue_date.isoformat(),
        'entries': [queue_payload(entry) for entry in entries],
        'statistics': queue_statistics(entries)
    })

@app.route('/api/queue/next', methods=['POST'])
def call_next_queue_patient():
    access_error = pharmacy_api_required(QUEUE_STAFF_ROLES)
    if access_error:
        return access_error
    data = request.get_json(silent=True) or {}
    query = Appointment.query.join(Doctor).filter(Appointment.queue_date == date.today(), Appointment.queue_status == 'Waiting')
    if data.get('doctor_id'):
        try:
            query = query.filter(Appointment.doctor_id == int(data['doctor_id']))
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid doctor filter'}), 400
    if data.get('department_id'):
        try:
            query = query.filter(Doctor.department_id == int(data['department_id']))
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid department filter'}), 400
    appointment = query.order_by(Appointment.token_number, Appointment.appointment_date).first()
    if not appointment:
        return jsonify({'error': 'No waiting patients in this queue'}), 404
    appointment.queue_status = 'Called'
    appointment.called_at = datetime.now()
    db.session.commit()
    return jsonify({'success': True, 'message': f'Token {appointment.token_number} called', 'entry': queue_payload(appointment)})

@app.route('/api/queue/<int:appointment_id>', methods=['PUT'])
def update_queue_status(appointment_id):
    access_error = pharmacy_api_required(QUEUE_STAFF_ROLES)
    if access_error:
        return access_error
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({'error': 'Queue appointment not found'}), 404
    data = request.get_json(silent=True) or {}
    new_status = (data.get('queue_status') or '').strip()
    if new_status not in QUEUE_STATUSES:
        return jsonify({'error': 'Invalid queue status'}), 400
    current_status = appointment.queue_status or 'Waiting'
    if current_status in {'Completed', 'No Show'} and new_status not in {'Completed', 'No Show'}:
        return jsonify({'error': 'Completed or no-show patients cannot be returned to the active queue'}), 409
    appointment.queue_status = new_status
    if new_status == 'Called' and not appointment.called_at:
        appointment.called_at = datetime.now()
    if new_status == 'In Consultation' and not appointment.consultation_started_at:
        appointment.consultation_started_at = datetime.now()
    if new_status == 'Completed':
        appointment.queue_completed_at = appointment.queue_completed_at or datetime.now()
        appointment.status = 'Completed'
    if new_status == 'No Show':
        appointment.queue_completed_at = appointment.queue_completed_at or datetime.now()
        appointment.status = 'Cancelled'
    db.session.commit()
    return jsonify({'success': True, 'message': 'Queue status updated', 'entry': queue_payload(appointment)})

@app.route('/api/queue/walk-ins', methods=['POST'])
def create_walk_in():
    access_error = pharmacy_api_required({'admin', 'receptionist', 'doctor'})
    if access_error:
        return access_error
    data = request.get_json(silent=True) or {}
    patient_name = (data.get('patient_name') or '').strip()
    patient_email = (data.get('patient_email') or '').strip()
    patient_phone = (data.get('patient_phone') or '').strip()
    reason = (data.get('reason') or '').strip() or None
    try:
        doctor_id = int(data.get('doctor_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'A valid doctor is required'}), 400
    doctor = Doctor.query.get(doctor_id)
    if not all([patient_name, patient_email, patient_phone]) or not doctor:
        return jsonify({'error': 'Patient name, email, phone, and doctor are required'}), 400
    appointment_datetime = datetime.now()
    user_id = session.get('user_id') if User.query.get(session['user_id']).user_type == 'patient' else data.get('user_id')
    try:
        user_id = int(user_id) if user_id else None
    except (TypeError, ValueError):
        user_id = None
    duplicate = active_queue_duplicate(patient_email, user_id, doctor.id, appointment_datetime)
    if duplicate:
        return jsonify({'error': 'This patient already has an active token for this doctor and time slot', 'entry': queue_payload(duplicate)}), 409
    appointment = Appointment(
        user_id=user_id,
        patient_name=patient_name,
        patient_email=patient_email,
        patient_phone=patient_phone,
        doctor_id=doctor.id,
        appointment_date=appointment_datetime,
        reason=reason,
        token_number=next_queue_token(doctor.id, appointment_datetime.date()),
        queue_date=appointment_datetime.date(),
        queue_status='Waiting'
    )
    db.session.add(appointment)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Walk-in token generated', 'entry': queue_payload(appointment)}), 201

# ==================== APPOINTMENTS ====================

@app.route('/appointments')
def appointments_page():
    doctors = Doctor.query.all()
    return render_template('appointments.html', doctors=doctors)

@app.route('/calendar')
@login_required
def calendar_page():
    appointments = Appointment.query.all() if session.get('user_type') == 'admin' else Appointment.query.filter_by(user_id=session['user_id']).all()
    return render_template('calendar.html', appointments=appointments)

@app.route('/admin-reports')
@admin_required
def admin_reports():
    return render_template('admin_reports.html',
                           total_users=User.query.filter_by(user_type='patient').count(),
                           total_doctors=Doctor.query.count(),
                           total_services=Service.query.count(),
                           total_appointments=Appointment.query.count(),
                           total_bills=Bill.query.count(),
                           pending_bills=Bill.query.filter_by(status='Pending').count(),
                           paid_bills=Bill.query.filter_by(status='Paid').count())

def analytics_date_range(start_value=None, end_value=None):
    today = date.today()
    try:
        start_date = date.fromisoformat(start_value) if start_value else today - timedelta(days=365)
        end_date = date.fromisoformat(end_value) if end_value else today
    except ValueError:
        raise ValueError('Date filters must be valid dates')
    if start_date > end_date:
        raise ValueError('Start date cannot be after end date')
    return start_date, end_date, datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date + timedelta(days=1), datetime.min.time())

def analytics_month_keys(start_date, end_date):
    current = start_date.replace(day=1)
    end_month = end_date.replace(day=1)
    months = []
    while current <= end_month:
        months.append(current.strftime('%Y-%m'))
        current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
    return months

@app.route('/analytics')
@admin_required
def analytics_page():
    return render_template('analytics.html', departments=Department.query.filter_by(status='Active').order_by(Department.name).all())

@app.route('/api/analytics')
@admin_required
def api_analytics():
    try:
        start_date, end_date, start_datetime, end_datetime = analytics_date_range(request.args.get('start_date'), request.args.get('end_date'))
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    department_id = request.args.get('department_id')
    if department_id:
        try:
            department_id = int(department_id)
        except ValueError:
            return jsonify({'error': 'Department filter must be a valid ID'}), 400

    appointment_query = Appointment.query.filter(Appointment.appointment_date >= start_datetime, Appointment.appointment_date < end_datetime)
    if department_id:
        appointment_query = appointment_query.join(Doctor).filter(Doctor.department_id == department_id)
    appointments_in_range = appointment_query.count()
    today_appointments_query = Appointment.query.filter(func.date(Appointment.appointment_date) == date.today().isoformat())
    if department_id:
        today_appointments_query = today_appointments_query.join(Doctor).filter(Doctor.department_id == department_id)
    today_appointments = today_appointments_query.count()
    completed_appointments = appointment_query.filter(Appointment.status == 'Completed').count()

    patient_query = User.query.filter_by(user_type='patient')
    total_patients = patient_query.count()
    new_patients = patient_query.filter(User.created_at >= start_datetime, User.created_at < end_datetime).count()

    bill_query = Bill.query.filter(Bill.created_at >= start_datetime, Bill.created_at < end_datetime)
    if department_id:
        bill_query = bill_query.outerjoin(Appointment, Bill.appointment_id == Appointment.id).outerjoin(Doctor, Appointment.doctor_id == Doctor.id).filter((Doctor.department_id == department_id) | (Bill.appointment_id.is_(None)))
    revenue = db.session.query(func.coalesce(func.sum(Bill.amount), 0)).filter(Bill.status == 'Paid', Bill.created_at >= start_datetime, Bill.created_at < end_datetime)
    pending_payments = db.session.query(func.coalesce(func.sum(Bill.amount), 0)).filter(Bill.status != 'Paid', Bill.created_at >= start_datetime, Bill.created_at < end_datetime)
    if department_id:
        revenue = revenue.outerjoin(Appointment, Bill.appointment_id == Appointment.id).outerjoin(Doctor, Appointment.doctor_id == Doctor.id).filter((Doctor.department_id == department_id) | (Bill.appointment_id.is_(None)))
        pending_payments = pending_payments.outerjoin(Appointment, Bill.appointment_id == Appointment.id).outerjoin(Doctor, Appointment.doctor_id == Doctor.id).filter((Doctor.department_id == department_id) | (Bill.appointment_id.is_(None)))

    month_keys = analytics_month_keys(start_date, end_date)
    patient_rows = db.session.query(func.strftime('%Y-%m', User.created_at), func.count(User.id)).filter(User.user_type == 'patient', User.created_at >= start_datetime, User.created_at < end_datetime).group_by(func.strftime('%Y-%m', User.created_at)).all()
    appointment_month_query = db.session.query(func.strftime('%Y-%m', Appointment.appointment_date), func.count(Appointment.id)).filter(Appointment.appointment_date >= start_datetime, Appointment.appointment_date < end_datetime)
    if department_id:
        appointment_month_query = appointment_month_query.join(Doctor).filter(Doctor.department_id == department_id)
    appointment_rows = appointment_month_query.group_by(func.strftime('%Y-%m', Appointment.appointment_date)).all()
    revenue_month_query = db.session.query(func.strftime('%Y-%m', Bill.created_at), func.coalesce(func.sum(Bill.amount), 0)).filter(Bill.status == 'Paid', Bill.created_at >= start_datetime, Bill.created_at < end_datetime)
    if department_id:
        revenue_month_query = revenue_month_query.outerjoin(Appointment, Bill.appointment_id == Appointment.id).outerjoin(Doctor, Appointment.doctor_id == Doctor.id).filter((Doctor.department_id == department_id) | (Bill.appointment_id.is_(None)))
    revenue_rows = revenue_month_query.group_by(func.strftime('%Y-%m', Bill.created_at)).all()

    status_query = db.session.query(Appointment.status, func.count(Appointment.id)).filter(Appointment.appointment_date >= start_datetime, Appointment.appointment_date < end_datetime)
    if department_id:
        status_query = status_query.join(Doctor).filter(Doctor.department_id == department_id)
    status_rows = status_query.group_by(Appointment.status).all()
    department_rows = db.session.query(Department.name, func.count(distinct(Appointment.user_id))).join(Doctor, Doctor.department_id == Department.id).join(Appointment, Appointment.doctor_id == Doctor.id).filter(Appointment.appointment_date >= start_datetime, Appointment.appointment_date < end_datetime).group_by(Department.id, Department.name).order_by(Department.name).all()
    if department_id:
        department_rows = [row for row in department_rows if Department.query.filter_by(id=department_id, name=row[0]).first()]
    bed_rows = db.session.query(Bed.status, func.count(Bed.id)).group_by(Bed.status).all()
    pharmacy_stock = db.session.query(func.coalesce(func.sum(Medicine.quantity), 0)).scalar() or 0
    pending_lab_tests = LabTest.query.filter(LabTest.status != 'Completed', LabTest.scheduled_date >= start_datetime, LabTest.scheduled_date < end_datetime).count()

    def series(rows):
        values = {key: value for key, value in rows}
        return [values.get(month, 0) for month in month_keys]

    bed_counts = {status: count for status, count in bed_rows}
    return jsonify({
        'filters': {'start_date': start_date.isoformat(), 'end_date': end_date.isoformat(), 'department_id': department_id},
        'cards': {'total_patients': total_patients, 'new_patients': new_patients, 'today_appointments': today_appointments, 'completed_appointments': completed_appointments, 'revenue': float(revenue.scalar() or 0), 'pending_payments': float(pending_payments.scalar() or 0), 'available_beds': bed_counts.get('Available', 0), 'occupied_beds': bed_counts.get('Occupied', 0), 'pharmacy_stock': pharmacy_stock, 'pending_lab_tests': pending_lab_tests},
        'charts': {'labels': month_keys, 'patients_per_month': series(patient_rows), 'appointments_per_month': series(appointment_rows), 'revenue_per_month': [float(value) for value in series(revenue_rows)], 'department_patients': {'labels': [row[0] for row in department_rows], 'values': [row[1] for row in department_rows]}, 'appointment_status': {'labels': [row[0] or 'Unknown' for row in status_rows], 'values': [row[1] for row in status_rows]}, 'bed_occupancy': {'labels': list(bed_counts.keys()), 'values': list(bed_counts.values())}}
    })

@app.route('/api/appointments', methods=['GET', 'POST'])
def api_appointments():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        try:
            appointment_datetime = datetime.fromisoformat(data.get('appointment_date'))
            doctor_id = int(data.get('doctor_id'))
        except (TypeError, ValueError):
            return jsonify({'error': 'Doctor and a valid appointment date are required'}), 400
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        
        user_id = None
        if 'user_id' in session:
            user_id = session['user_id']
        duplicate = active_queue_duplicate(data.get('patient_email'), user_id, doctor.id, appointment_datetime)
        if duplicate:
            return jsonify({'error': 'This patient already has an active token for this doctor and time slot', 'entry': queue_payload(duplicate)}), 409
        
        appointment = Appointment(
            user_id=user_id,
            patient_name=data.get('patient_name'),
            patient_email=data.get('patient_email'),
            patient_phone=data.get('patient_phone'),
            doctor_id=doctor.id,
            appointment_date=appointment_datetime,
            reason=data.get('reason'),
            token_number=next_queue_token(doctor.id, appointment_datetime.date()),
            queue_date=appointment_datetime.date(),
            queue_status='Waiting'
        )
        db.session.add(appointment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Appointment booked successfully', 'id': appointment.id, 'token_number': appointment.token_number, 'queue_status': appointment.queue_status})
    
    appointments = Appointment.query.all()
    return jsonify([{
        'id': a.id,
        'patient_name': a.patient_name,
        'patient_email': a.patient_email,
        'doctor_name': a.doctor.name,
        'department_name': a.doctor.department.name if a.doctor.department else None,
        'token_number': a.token_number,
        'queue_status': a.queue_status or 'Waiting',
        'appointment_date': a.appointment_date.isoformat(),
        'reason': a.reason,
        'status': a.status
    } for a in appointments])

@app.route('/api/appointments/<int:appointment_id>', methods=['GET', 'PUT', 'DELETE'])
def api_appointment_detail(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({'error': 'Appointment not found'}), 404
    
    if request.method == 'PUT':
        access_error = admin_api_required()
        if access_error:
            return access_error
        data = request.get_json()
        appointment.status = data.get('status', appointment.status)
        if appointment.status == 'Completed':
            appointment.queue_status = 'Completed'
            appointment.queue_completed_at = appointment.queue_completed_at or datetime.now()
        elif appointment.status == 'Cancelled':
            appointment.queue_status = 'No Show'
            appointment.queue_completed_at = appointment.queue_completed_at or datetime.now()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Appointment updated'})
    
    elif request.method == 'DELETE':
        access_error = admin_api_required()
        if access_error:
            return access_error
        db.session.delete(appointment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Appointment deleted'})
    
    return jsonify({
        'id': appointment.id,
        'patient_name': appointment.patient_name,
        'doctor_name': appointment.doctor.name,
        'department_name': appointment.doctor.department.name if appointment.doctor.department else None,
        'token_number': appointment.token_number,
        'queue_status': appointment.queue_status or 'Waiting',
        'appointment_date': appointment.appointment_date.isoformat(),
        'status': appointment.status
    })

@app.route('/admin/appointments/<int:appointment_id>/confirm', methods=['POST'])
@admin_required
def confirm_appointment(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        flash('Appointment not found', 'danger')
        return redirect(url_for('admin_dashboard', _anchor='appointments'))

    appointment.status = 'Confirmed'
    db.session.commit()
    flash(f'Appointment #{appointment.id} confirmed successfully', 'success')
    return redirect(url_for('admin_dashboard', _anchor='appointments'))

# ==================== BILLING ====================

def invoice_number_for_bill(bill):
    return bill.invoice_number or f'INV-{bill.created_at.year}-{bill.id:06d}'

def invoice_line_payload(bill):
    description = bill.description or (bill.service.name if bill.service else 'Hospital service')
    searchable = f'{description} {bill.service.category if bill.service else ""}'.lower()
    if bill.appointment and bill.appointment.doctor:
        category = 'Doctor consultation'
        description = description if description != 'Hospital service' else f'Doctor consultation - Dr. {bill.appointment.doctor.name}'
    elif 'lab' in searchable or 'diagnostic' in searchable or 'test' in searchable:
        category = 'Lab charges'
    elif 'pharmacy' in searchable or 'medicine' in searchable or 'drug' in searchable:
        category = 'Pharmacy charges'
    elif 'room' in searchable or 'bed' in searchable or 'ward' in searchable:
        category = 'Room / bed charges'
    else:
        category = 'Service'
    return {'id': bill.id, 'category': category, 'description': description, 'amount': bill.amount}

def invoice_payload(bills):
    bills = sorted(bills, key=lambda bill: (bill.created_at, bill.id))
    first = bills[0]
    subtotal = sum(bill.amount for bill in bills)
    discount = first.discount_amount or 0
    tax = first.tax_amount or 0
    payment_dates = [bill.payment_date for bill in bills if bill.payment_date]
    statuses = {bill.status for bill in bills}
    status = 'Paid' if statuses and statuses.issubset({'Paid'}) else 'Pending'
    return {
        'invoice_number': invoice_number_for_bill(first),
        'bill_ids': [bill.id for bill in bills],
        'generated': bool(first.invoice_number),
        'patient': {'id': first.user_id, 'name': first.patient_name, 'email': first.patient_email},
        'lines': [invoice_line_payload(bill) for bill in bills],
        'subtotal': subtotal,
        'discount': discount,
        'tax': tax,
        'total': max(0, subtotal - discount + tax),
        'status': status,
        'payment_date': max(payment_dates).isoformat() if payment_dates else None,
        'created_at': first.created_at.isoformat(),
        'due_date': max((bill.due_date for bill in bills if bill.due_date), default=None).isoformat() if any(bill.due_date for bill in bills) else None
    }

def grouped_invoices(bills):
    groups = {}
    for bill in bills:
        groups.setdefault(invoice_number_for_bill(bill), []).append(bill)
    return [invoice_payload(group) for group in groups.values()]

@app.route('/invoices')
@login_required
def invoices_page():
    user = User.query.get(session['user_id'])
    return render_template('invoices.html', is_admin=user.user_type == 'admin')

@app.route('/api/invoices', methods=['GET'])
@login_required
def api_invoices():
    user = User.query.get(session['user_id'])
    query = Bill.query
    if user.user_type == 'patient':
        query = query.filter_by(user_id=user.id)
    elif user.user_type != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    bills = query.order_by(Bill.created_at.desc()).all()
    search = (request.args.get('q') or '').strip().lower()
    status = (request.args.get('status') or '').strip().lower()
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    if search:
        bills = [bill for bill in bills if search in invoice_number_for_bill(bill).lower() or search in bill.patient_name.lower() or search in (bill.description or '').lower() or (bill.service and search in bill.service.name.lower())]
    if status in {'paid', 'pending'}:
        bills = [bill for bill in bills if (bill.status or 'Pending').lower() == status]
    try:
        if date_from:
            bills = [bill for bill in bills if bill.created_at.date() >= date.fromisoformat(date_from)]
        if date_to:
            bills = [bill for bill in bills if bill.created_at.date() <= date.fromisoformat(date_to)]
    except ValueError:
        return jsonify({'error': 'Invoice date filters must be valid dates'}), 400
    invoices = grouped_invoices(bills)
    return jsonify({'invoices': invoices, 'statistics': {
        'invoice_count': len(invoices),
        'subtotal': sum(invoice['subtotal'] for invoice in invoices),
        'pending_total': sum(invoice['total'] for invoice in invoices if invoice['status'] != 'Paid'),
        'paid_total': sum(invoice['total'] for invoice in invoices if invoice['status'] == 'Paid')
    }})

@app.route('/api/invoices/generate', methods=['POST'])
def generate_invoice():
    access_error = admin_api_required()
    if access_error:
        return access_error
    data = request.get_json(silent=True) or {}
    try:
        bill_ids = [int(bill_id) for bill_id in data.get('bill_ids', [])]
    except (TypeError, ValueError):
        return jsonify({'error': 'Bill IDs must be valid integers'}), 400
    if not bill_ids:
        return jsonify({'error': 'Select at least one existing bill'}), 400
    bills = Bill.query.filter(Bill.id.in_(bill_ids)).order_by(Bill.id).all()
    if len(bills) != len(set(bill_ids)):
        return jsonify({'error': 'One or more bills could not be found'}), 404
    if len({bill.user_id or bill.patient_email for bill in bills}) != 1:
        return jsonify({'error': 'An invoice can contain charges for one patient only'}), 400
    existing_numbers = {bill.invoice_number for bill in bills if bill.invoice_number}
    if len(existing_numbers) > 1:
        return jsonify({'error': 'Selected bills already belong to different invoices'}), 409
    number = next(iter(existing_numbers), f'INV-{datetime.now().year}-{bills[0].id:06d}')
    try:
        discount = max(0, float(data.get('discount', 0) or 0))
        tax = max(0, float(data.get('tax', 0) or 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Discount and tax must be valid amounts'}), 400
    if discount > sum(bill.amount for bill in bills):
        return jsonify({'error': 'Discount cannot exceed the subtotal'}), 400
    for bill in bills:
        bill.invoice_number = number
    bills[0].discount_amount = discount
    bills[0].tax_amount = tax
    db.session.commit()
    return jsonify({'success': True, 'invoice': invoice_payload(bills)}), 201

@app.route('/api/invoices/<path:invoice_number>/pdf')
@login_required
def invoice_pdf(invoice_number):
    user = User.query.get(session['user_id'])
    bills = Bill.query.filter((Bill.invoice_number == invoice_number) | (Bill.id == int(invoice_number.removeprefix('INV-').split('-')[-1]) if invoice_number.startswith('INV-') and invoice_number.removeprefix('INV-').split('-')[-1].isdigit() else False)).all()
    if not bills or (user.user_type == 'patient' and any(bill.user_id != user.id for bill in bills)):
        return jsonify({'error': 'Invoice not found'}), 404
    if user.user_type not in {'admin', 'patient'}:
        return jsonify({'error': 'Access denied'}), 403
    invoice = invoice_payload(bills)
    try:
        from io import BytesIO
        from xml.sax.saxutils import escape
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return jsonify({'error': 'PDF support is not installed. Install the application requirements.'}), 503
    hospital = HospitalInfo.query.first() or HospitalInfo()
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='InvoiceHospital', parent=styles['Title'], fontSize=21, leading=25, textColor=colors.HexColor('#123b52'), alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='InvoiceSmall', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#5b6870')))
    styles.add(ParagraphStyle(name='InvoiceBody', parent=styles['Normal'], fontSize=9.5, leading=13, textColor=colors.HexColor('#202a30')))
    safe = lambda value: escape(str(value or 'Not provided')).replace('\n', '<br/>')
    story = [Paragraph(safe(hospital.name), styles['InvoiceHospital']), Paragraph(safe(hospital.address) + ' | ' + safe(hospital.phone) + ' | ' + safe(hospital.email), styles['InvoiceSmall']), Spacer(1, 10), Paragraph('<b>INVOICE</b> ' + safe(invoice['invoice_number']), styles['Heading2'])]
    details = Table([[Paragraph('<b>Billed to</b><br/>' + safe(invoice['patient']['name']) + '<br/>' + safe(invoice['patient']['email']), styles['InvoiceBody']), Paragraph('<b>Invoice date</b><br/>' + safe(invoice['created_at'][:10]) + '<br/><b>Status:</b> ' + safe(invoice['status']), styles['InvoiceBody'])]], colWidths=[100 * mm, 72 * mm])
    details.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f3f7f9')), ('BOX', (0, 0), (-1, -1), .5, colors.HexColor('#c9d8df')), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('PADDING', (0, 0), (-1, -1), 8)]))
    story += [details, Spacer(1, 12)]
    rows = [[Paragraph('<b>Category</b>', styles['InvoiceBody']), Paragraph('<b>Description</b>', styles['InvoiceBody']), Paragraph('<b>Amount</b>', styles['InvoiceBody'])]]
    rows += [[Paragraph(safe(line['category']), styles['InvoiceBody']), Paragraph(safe(line['description']), styles['InvoiceBody']), Paragraph(f"${line['amount']:.2f}", styles['InvoiceBody'])] for line in invoice['lines']]
    rows += [['', Paragraph('<b>Subtotal</b>', styles['InvoiceBody']), Paragraph(f"${invoice['subtotal']:.2f}", styles['InvoiceBody'])], ['', Paragraph('<b>Discount</b>', styles['InvoiceBody']), Paragraph(f"-${invoice['discount']:.2f}", styles['InvoiceBody'])], ['', Paragraph('<b>Tax</b>', styles['InvoiceBody']), Paragraph(f"${invoice['tax']:.2f}", styles['InvoiceBody'])], ['', Paragraph('<b>Total</b>', styles['InvoiceBody']), Paragraph(f"<b>${invoice['total']:.2f}</b>", styles['InvoiceBody'])]]
    table = Table(rows, colWidths=[42 * mm, 98 * mm, 32 * mm], repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e7f1f4')), ('BOX', (0, 0), (-1, -1), .5, colors.HexColor('#c9d8df')), ('INNERGRID', (0, 0), (-1, -1), .25, colors.HexColor('#dbe5e9')), ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('PADDING', (0, 0), (-1, -1), 7)]))
    story += [table, Spacer(1, 18), Paragraph('Thank you for choosing ' + safe(hospital.name) + '.', styles['InvoiceSmall'])]
    document.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=request.args.get('print') != '1', download_name=f'{invoice["invoice_number"]}.pdf')

@app.route('/bills')
def bills_page():
    bills = Bill.query.filter_by(user_id=session['user_id']).all() if session.get('user_type') == 'patient' else Bill.query.all()
    services = Service.query.all()
    return render_template('bills.html', bills=bills, services=services)

@app.route('/api/bills', methods=['GET', 'POST'])
def api_bills():
    if request.method == 'POST':
        access_error = admin_api_required()
        if access_error:
            return access_error
        data = request.get_json()
        due_date = datetime.now() + timedelta(days=30)
        
        user_id = None
        if 'user_id' in session:
            user_id = session['user_id']
        
        bill = Bill(
            user_id=user_id,
            patient_name=data.get('patient_name'),
            patient_email=data.get('patient_email'),
            service_id=int(data.get('service_id')),
            amount=float(data.get('amount')),
            description=data.get('description'),
            due_date=due_date
        )
        db.session.add(bill)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Bill created', 'id': bill.id})
    
    bills = Bill.query.filter_by(user_id=session['user_id']).all() if session.get('user_type') == 'patient' else Bill.query.all()
    return jsonify([{
        'id': b.id,
        'patient_name': b.patient_name,
        'amount': b.amount,
        'status': b.status,
        'created_at': b.created_at.isoformat(),
        'due_date': b.due_date.isoformat() if b.due_date else None
    } for b in bills])

@app.route('/api/bills/<int:bill_id>', methods=['GET', 'PUT', 'DELETE'])
def api_bill_detail(bill_id):
    bill = Bill.query.get(bill_id)
    if not bill:
        return jsonify({'error': 'Bill not found'}), 404
    
    if request.method == 'PUT':
        access_error = admin_api_required()
        if access_error:
            return access_error
        data = request.get_json()
        bill.status = data.get('status', bill.status)
        if bill.status == 'Paid':
            bill.payment_date = bill.payment_date or datetime.now()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Bill updated'})
    
    elif request.method == 'DELETE':
        access_error = admin_api_required()
        if access_error:
            return access_error
        db.session.delete(bill)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Bill deleted'})
    
    return jsonify({
        'id': bill.id,
        'patient_name': bill.patient_name,
        'amount': bill.amount,
        'status': bill.status
    })

# ==================== RATINGS ====================

@app.route('/api/ratings', methods=['GET', 'POST'])
def api_ratings():
    if request.method == 'POST':
        data = request.get_json()
        rating = Rating(
            patient_name=data.get('patient_name'),
            rating=int(data.get('rating')),
            comment=data.get('comment')
        )
        db.session.add(rating)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Rating submitted'})
    
    ratings = Rating.query.all()
    return jsonify([{
        'id': r.id,
        'patient_name': r.patient_name,
        'rating': r.rating,
        'comment': r.comment
    } for r in ratings])

# ==================== SEARCH ====================

@app.route('/api/search')
def search():
    query = request.args.get('q', '').lower()
    
    results = {
        'doctors': [],
        'services': [],
        'staff': []
    }
    
    if query:
        doctors = Doctor.query.filter(
            db.or_(
                Doctor.name.ilike(f'%{query}%'),
                Doctor.specialization.ilike(f'%{query}%')
            )
        ).all()
        
        services = Service.query.filter(
            db.or_(
                Service.name.ilike(f'%{query}%'),
                Service.category.ilike(f'%{query}%')
            )
        ).all()
        
        staff = Staff.query.filter(
            db.or_(
                Staff.name.ilike(f'%{query}%'),
                Staff.position.ilike(f'%{query}%'),
                Staff.department.ilike(f'%{query}%')
            )
        ).all()
        
        results['doctors'] = [{'id': d.id, 'name': d.name, 'specialization': d.specialization} for d in doctors]
        results['services'] = [{'id': s.id, 'name': s.name, 'charge': s.charge} for s in services]
        results['staff'] = [{'id': s.id, 'name': s.name, 'position': s.position} for s in staff]
    
    return jsonify(results)

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# ==================== INITIALIZE DATABASE ====================

def init_db():
    with app.app_context():
        db.create_all()
        doctor_columns = {column['name'] for column in inspect(db.engine).get_columns('doctor')}
        if 'department_id' not in doctor_columns:
            db.session.execute(text('ALTER TABLE doctor ADD COLUMN department_id INTEGER REFERENCES department(id)'))
            db.session.commit()
        appointment_columns = {column['name'] for column in inspect(db.engine).get_columns('appointment')}
        appointment_column_definitions = {
            'token_number': 'INTEGER',
            'queue_date': 'DATE',
            'queue_status': 'VARCHAR(30)',
            'called_at': 'DATETIME',
            'consultation_started_at': 'DATETIME',
            'queue_completed_at': 'DATETIME'
        }
        for column_name, column_definition in appointment_column_definitions.items():
            if column_name not in appointment_columns:
                db.session.execute(text(f'ALTER TABLE appointment ADD COLUMN {column_name} {column_definition}'))
        prescription_columns = {column['name'] for column in inspect(db.engine).get_columns('prescription')}
        prescription_column_definitions = {
            'doctor_id': 'INTEGER REFERENCES doctor(id)',
            'frequency': 'VARCHAR(100)',
            'duration': 'VARCHAR(100)',
            'diagnosis': 'TEXT',
            'follow_up_date': 'DATE',
            'signature_name': 'VARCHAR(100)'
        }
        for column_name, column_definition in prescription_column_definitions.items():
            if column_name not in prescription_columns:
                db.session.execute(text(f'ALTER TABLE prescription ADD COLUMN {column_name} {column_definition}'))
        bill_columns = {column['name'] for column in inspect(db.engine).get_columns('bill')}
        bill_column_definitions = {
            'invoice_number': 'VARCHAR(40)',
            'discount_amount': 'FLOAT',
            'tax_amount': 'FLOAT',
            'payment_date': 'DATETIME'
        }
        for column_name, column_definition in bill_column_definitions.items():
            if column_name not in bill_columns:
                db.session.execute(text(f'ALTER TABLE bill ADD COLUMN {column_name} {column_definition}'))
        db.session.commit()
        appointments_to_backfill = Appointment.query.order_by(Appointment.doctor_id, Appointment.appointment_date, Appointment.id).all()
        token_counters = {}
        for appointment in appointments_to_backfill:
            if appointment.queue_date is None:
                appointment.queue_date = appointment.appointment_date.date()
            queue_key = (appointment.doctor_id, appointment.queue_date)
            token_counters[queue_key] = token_counters.get(queue_key, 0) + 1
            if appointment.token_number is None:
                appointment.token_number = token_counters[queue_key]
            if not appointment.queue_status:
                appointment.queue_status = 'Completed' if appointment.status == 'Completed' else 'No Show' if appointment.status == 'Cancelled' else 'Waiting'
        db.session.commit()
        
        # Add default data
        if HospitalInfo.query.first() is None:
            hospital = HospitalInfo()
            db.session.add(hospital)
        
        # Add or refresh default admin user
        admin_username = 'ashishyadav977'
        admin_password = 'ashish2004'
        admin_email = 'ashishyadav977@hospital.com'
        admin = User.query.filter_by(username=admin_username).first()
        if admin is None:
            admin = User.query.filter_by(user_type='admin').first()

        if admin is None:
            admin = User(
                username=admin_username,
                email=admin_email,
                full_name='System Administrator',
                user_type='admin'
            )
            admin.set_password(admin_password)
            db.session.add(admin)
        else:
            admin.username = admin_username
            admin.email = admin_email
            admin.full_name = 'System Administrator'
            admin.user_type = 'admin'
            admin.set_password(admin_password)

        department_defaults = [
            ('Cardiology', 'Heart and cardiovascular care', '555-0201', 'cardiology@hospital.com'),
            ('Neurology', 'Brain and nervous system care', '555-0202', 'neurology@hospital.com'),
            ('Orthopedics', 'Bone, joint, and musculoskeletal care', '555-0203', 'orthopedics@hospital.com'),
            ('Pediatrics', 'Medical care for children', '555-0204', 'pediatrics@hospital.com'),
            ('General Medicine', 'Comprehensive adult medical care', '555-0205', 'general.medicine@hospital.com'),
            ('Emergency', 'Immediate and urgent medical care', '555-0206', 'emergency@hospital.com'),
            ('ICU', 'Critical and intensive care services', '555-0207', 'icu@hospital.com')
        ]
        for name, description, phone, email in department_defaults:
            if not Department.query.filter(db.func.lower(Department.name) == name.lower()).first():
                db.session.add(Department(name=name, description=description, phone=phone, email=email, status='Active'))
        db.session.flush()
        
        # Add sample doctors
        if Doctor.query.count() == 0:
            sample_doctors = [
                Doctor(name='Dr. Sarah Johnson', specialization='Cardiology', experience=15, 
                       phone='555-0101', email='sarah.johnson@hospital.com', bio='Expert in heart diseases'),
                Doctor(name='Dr. Michael Chen', specialization='Neurology', experience=12,
                       phone='555-0102', email='michael.chen@hospital.com', bio='Brain and nervous system specialist'),
                Doctor(name='Dr. Emily Roberts', specialization='Orthopedics', experience=10,
                       phone='555-0103', email='emily.roberts@hospital.com', bio='Bone and joint specialist'),
                Doctor(name='Dr. James Wilson', specialization='Pediatrics', experience=8,
                       phone='555-0104', email='james.wilson@hospital.com', bio='Children healthcare specialist'),
            ]
            db.session.add_all(sample_doctors)

        db.session.flush()
        specialization_departments = {
            'cardiology': 'Cardiology',
            'neurology': 'Neurology',
            'orthopedics': 'Orthopedics',
            'pediatrics': 'Pediatrics'
        }
        departments_by_name = {department.name: department for department in Department.query.all()}
        for doctor in Doctor.query.all():
            if doctor.department_id is None:
                target_name = specialization_departments.get(doctor.specialization.lower())
                if target_name in departments_by_name:
                    doctor.department = departments_by_name[target_name]
        for specialization, department_name in specialization_departments.items():
            department = departments_by_name.get(department_name)
            if department and department.head_doctor_id is None:
                head_doctor = Doctor.query.filter(db.func.lower(Doctor.specialization) == specialization).first()
                if head_doctor:
                    department.head_doctor = head_doctor
        
        # Add sample services
        if Service.query.count() == 0:
            sample_services = [
                Service(name='General Consultation', description='Initial doctor consultation', charge=50, category='Consultation'),
                Service(name='CT Scan', description='Computed Tomography Scan', charge=300, category='Diagnostics'),
                Service(name='Blood Test', description='Complete blood examination', charge=75, category='Laboratory'),
                Service(name='X-Ray', description='X-Ray imaging', charge=100, category='Diagnostics'),
                Service(name='Surgical Operation', description='Surgery services', charge=1500, category='Surgery'),
                Service(name='Emergency Care', description='24/7 Emergency services', charge=200, category='Emergency'),
            ]
            db.session.add_all(sample_services)

        if Bed.query.count() == 0:
            sample_beds = []
            for ward, department, count in [
                ('General Ward', 'General Medicine', 6),
                ('Cardiology Ward', 'Cardiology', 4),
                ('Surgical Ward', 'Surgery', 4)
            ]:
                for number in range(1, count + 1):
                    sample_beds.append(Bed(
                        bed_number=f'{ward[:2].upper()}-{number:02d}',
                        department=department,
                        ward=ward,
                        status='Available'
                    ))
            db.session.add_all(sample_beds)
        
        db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
