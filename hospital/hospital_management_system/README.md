# Hospital Management System - Advanced Application

A professional, full-featured Hospital Management System built with Flask, SQLAlchemy, HTML5, CSS3, and JavaScript. This is an advanced-level application with an attractive user-friendly interface.

## Features

### 🏥 Core Features

1. **Doctor Information Management**
   - Add, edit, and delete doctors
   - Display doctor photos/images
   - Specialization and experience tracking
   - Doctor availability status
   - Bio and professional details

2. **Bill Management System**
   - Create and manage patient bills
   - Track payment status (Pending/Paid)
   - Service-based billing
   - Due date tracking
   - Bill summary dashboard

3. **Appointment System**
   - Book appointments with doctors
   - Real-time availability checking
   - Appointment status tracking (Pending/Confirmed/Completed/Cancelled)
   - Email and phone validation
   - Appointment history

4. **Service Charges**
   - Categorized services (Consultation, Diagnostics, Laboratory, Surgery, Emergency, etc.)
   - Dynamic pricing
   - Service descriptions
   - Integration with billing system

5. **Staff Management**
   - Add and manage staff members
   - Department assignment
   - Staff photos/profiles
   - Contact information
   - Position tracking

6. **Hospital Services**
   - Comprehensive service catalog
   - Service categorization
   - Service pricing
   - Service descriptions
   - Easy service management

7. **Hospital Rating System**
   - Patient rating submission
   - Star-based feedback (1-5 stars)
   - Comment section
   - Rating display on homepage
   - Overall hospital rating

8. **Search Functionality**
   - Global search bar in navigation
   - Search doctors by name/specialization
   - Search services by name/category
   - Search staff by name/position/department
   - Real-time search results

9. **Hospital Information Page**
   - Detailed hospital information
   - Mission and vision statements
   - Core values display
   - Contact information
   - Hospital statistics
   - Address and emergency numbers

## Project Structure

```
hospital_management_system/
│
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
│
├── templates/                      # HTML Templates
│   ├── base.html                  # Base template with navigation
│   ├── index.html                 # Homepage
│   ├── hospital_info.html         # Hospital information page
│   ├── doctors.html               # Doctors management page
│   ├── staff.html                 # Staff management page
│   ├── services.html              # Services management page
│   ├── appointments.html          # Appointments booking page
│   └── bills.html                 # Billing management page
│
├── static/                         # Static files
│   ├── css/
│   │   └── style.css              # Main stylesheet
│   │
│   ├── js/
│   │   └── main.js                # JavaScript functionality
│   │
│   └── images/
│       ├── doctors/               # Doctor images
│       └── uploads/               # Uploaded files
```

## Installation & Setup

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Step 1: Clone or Download the Project
```bash
cd hospital_management_system
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run the Application
```bash
python app.py
```

The application will start at: `http://localhost:5000`

## Database

- **Database Type**: SQLite (hospital.db)
- **Auto-initialization**: Database and tables are created automatically on first run
- **Sample Data**: Default hospital information and sample doctors/services are populated on initialization

## Default Features

### Pre-populated Data:
- 4 Sample Doctors (Cardiology, Neurology, Orthopedics, Pediatrics)
- 6 Sample Services (Consultation, CT Scan, Blood Test, X-Ray, Surgery, Emergency)
- Hospital Information with ratings and details

## API Endpoints

### Hospital Information
- `GET /api/hospital-info` - Get hospital information
- `POST /api/hospital-info` - Update hospital information

### Doctors
- `GET /api/doctors` - Get all doctors
- `POST /api/doctors` - Add new doctor
- `GET /api/doctors/<id>` - Get doctor details
- `PUT /api/doctors/<id>` - Update doctor
- `DELETE /api/doctors/<id>` - Delete doctor

### Staff
- `GET /api/staff` - Get all staff
- `POST /api/staff` - Add new staff member
- `GET /api/staff/<id>` - Get staff details

### Services
- `GET /api/services` - Get all services
- `POST /api/services` - Add new service
- `GET /api/services/<id>` - Get service details
- `DELETE /api/services/<id>` - Delete service

### Appointments
- `GET /api/appointments` - Get all appointments
- `POST /api/appointments` - Book new appointment
- `GET /api/appointments/<id>` - Get appointment details
- `PUT /api/appointments/<id>` - Update appointment
- `DELETE /api/appointments/<id>` - Cancel appointment

### Billing
- `GET /api/bills` - Get all bills
- `POST /api/bills` - Create new bill
- `GET /api/bills/<id>` - Get bill details
- `PUT /api/bills/<id>` - Update bill status
- `DELETE /api/bills/<id>` - Delete bill

### Ratings
- `GET /api/ratings` - Get all ratings
- `POST /api/ratings` - Submit new rating

### Search
- `GET /api/search?q=<query>` - Global search functionality

## User Interface Highlights

### Professional Design
- Modern gradient backgrounds
- Smooth animations and transitions
- Responsive grid layouts
- Professional color scheme
- Clean and intuitive navigation

### Mobile Responsive
- Fully responsive design
- Mobile-friendly navigation
- Touch-optimized buttons
- Adaptive layouts

### Interactive Features
- Modal dialogs for forms
- Real-time search
- Dynamic data loading
- Live table updates
- Status indicators
- Interactive star rating

## File Upload
- Support for doctor and staff photos (PNG, JPG, JPEG, GIF)
- Maximum file size: 16MB
- Automatic file naming to prevent conflicts

## Security Features
- CSRF protection ready
- SQL injection prevention (SQLAlchemy ORM)
- Input validation
- File type verification
- Secure file handling

## Browser Compatibility
- Chrome (recommended)
- Firefox
- Safari
- Edge
- Mobile browsers

## Performance Features
- Database indexing
- Efficient queries
- Client-side caching
- Responsive lazy loading
- Optimized CSS and JavaScript

## Future Enhancements
- User authentication system
- Email notifications
- SMS alerts
- Payment gateway integration
- Admin dashboard
- Advanced reporting
- Patient portal
- Multi-language support

## Troubleshooting

### Port Already in Use
If port 5000 is already in use, modify the port in app.py:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Database Issues
To reset the database, delete `hospital.db` and restart the application.

### Image Upload Issues
Ensure the `static/images/uploads` directory has write permissions.

## Support & Documentation

For detailed information about each feature, refer to the inline code comments and docstrings in `app.py`.

## License
This project is provided as-is for educational and commercial purposes.

## Version
**v1.0** - Advanced Hospital Management System
**Release Date**: 2024

---

**Built with**: Flask, SQLAlchemy, HTML5, CSS3, JavaScript
**Author**: Healthcare Solutions Team
