from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import json

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
    experience = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    image = db.Column(db.String(255))
    availability = db.Column(db.String(50), default='Available')
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

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
    service = db.relationship('Service', backref='bills')
    appointment = db.relationship('Appointment', backref='bills')

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
    
    return render_template('login.html')

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
    
    return render_template('user_dashboard.html', user=user, appointments=appointments, bills=bills)

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
    
    return render_template('admin_dashboard.html',
                         total_users=total_users,
                         total_appointments=total_appointments,
                         total_bills=total_bills,
                         pending_appointments=pending_appointments,
                         users=users,
                         appointments=appointments,
                         bills=bills)

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

# ==================== DOCTORS ====================

@app.route('/doctors')
def doctors():
    doctors_list = Doctor.query.all()
    return render_template('doctors.html', doctors=doctors_list)

@app.route('/api/doctors', methods=['GET', 'POST'])
def api_doctors():
    if request.method == 'POST':
        name = request.form.get('name')
        specialization = request.form.get('specialization')
        experience = request.form.get('experience')
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
        
        doctor = Doctor(
            name=name,
            specialization=specialization,
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
            'experience': doctor.experience,
            'phone': doctor.phone,
            'email': doctor.email,
            'image': doctor.image,
            'bio': doctor.bio
        })
    
    elif request.method == 'PUT':
        doctor.name = request.form.get('name', doctor.name)
        doctor.specialization = request.form.get('specialization', doctor.specialization)
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
        name = request.form.get('name')
        position = request.form.get('position')
        department = request.form.get('department')
        phone = request.form.get('phone')
        email = request.form.get('email')
        
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

@app.route('/api/services/<int:service_id>', methods=['GET', 'DELETE'])
def api_service_detail(service_id):
    service = Service.query.get(service_id)
    if not service:
        return jsonify({'error': 'Service not found'}), 404
    
    if request.method == 'DELETE':
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

# ==================== APPOINTMENTS ====================

@app.route('/appointments')
def appointments_page():
    doctors = Doctor.query.all()
    return render_template('appointments.html', doctors=doctors)

@app.route('/api/appointments', methods=['GET', 'POST'])
def api_appointments():
    if request.method == 'POST':
        data = request.get_json()
        appointment_datetime = datetime.fromisoformat(data.get('appointment_date'))
        
        user_id = None
        if 'user_id' in session:
            user_id = session['user_id']
        
        appointment = Appointment(
            user_id=user_id,
            patient_name=data.get('patient_name'),
            patient_email=data.get('patient_email'),
            patient_phone=data.get('patient_phone'),
            doctor_id=int(data.get('doctor_id')),
            appointment_date=appointment_datetime,
            reason=data.get('reason')
        )
        db.session.add(appointment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Appointment booked successfully', 'id': appointment.id})
    
    appointments = Appointment.query.all()
    return jsonify([{
        'id': a.id,
        'patient_name': a.patient_name,
        'patient_email': a.patient_email,
        'doctor_name': a.doctor.name,
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
        data = request.get_json()
        appointment.status = data.get('status', appointment.status)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Appointment updated'})
    
    elif request.method == 'DELETE':
        db.session.delete(appointment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Appointment deleted'})
    
    return jsonify({
        'id': appointment.id,
        'patient_name': appointment.patient_name,
        'doctor_name': appointment.doctor.name,
        'appointment_date': appointment.appointment_date.isoformat(),
        'status': appointment.status
    })

# ==================== BILLING ====================

@app.route('/bills')
def bills_page():
    bills = Bill.query.all()
    services = Service.query.all()
    return render_template('bills.html', bills=bills, services=services)

@app.route('/api/bills', methods=['GET', 'POST'])
def api_bills():
    if request.method == 'POST':
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
    
    bills = Bill.query.all()
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
        data = request.get_json()
        bill.status = data.get('status', bill.status)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Bill updated'})
    
    elif request.method == 'DELETE':
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
        
        # Add default data
        if HospitalInfo.query.first() is None:
            hospital = HospitalInfo()
            db.session.add(hospital)
        
        # Add default admin user
        if User.query.filter_by(username='AdminAR@gmail.com').first() is None:
            admin = User(
                username='AdminAR@gmail.com',
                email='AdminAR@gmail.com',
                full_name='System Administrator',
                user_type='admin'
            )
            admin.set_password('AshishRajesh')
            db.session.add(admin)
        
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
        
        db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
