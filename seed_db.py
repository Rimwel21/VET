import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.booking import Booking
from app.models.service import Service
from datetime import date, timedelta

app = create_app(os.getenv('FLASK_ENV', 'default'))

with app.app_context():
    print("Seeding database with mock data...")
    
    # 1. Ensure there is at least one service
    service = Service.query.first()
    if not service:
        print("Creating default service...")
        service = Service(name="General Checkup", icon="stethoscope", duration_minutes=30)
        db.session.add(service)
        db.session.commit()

    # 2. Create Mock Clients
    users_data = [
        {"first_name": "Sarah", "last_name": "Connor", "email": "sarah.connor@example.com", "contact": "555-0101"},
        {"first_name": "John", "last_name": "Wick", "email": "john.wick@example.com", "contact": "555-0102"},
        {"first_name": "Elle", "last_name": "Woods", "email": "elle.woods@example.com", "contact": "555-0103"}
    ]
    
    clients = []
    for ud in users_data:
        u = User.query.filter_by(email=ud['email']).first()
        if not u:
            u = User(first_name=ud['first_name'], last_name=ud['last_name'], email=ud['email'], contact=ud['contact'], role='client')
            u.set_password("password123")
            db.session.add(u)
        clients.append(u)
    
    db.session.commit()
    print("Mock clients added.")

    # 3. Create Mock Bookings for Several Days
    today = date.today()
    tomorrow = today + timedelta(days=1)
    day3 = today + timedelta(days=2)
    day4 = today + timedelta(days=3)
    
    bookings_data = [
        # Today's Appointments
        {"user": clients[0], "date": today, "slot": "9:00 AM", "pet_name": "Terminator", "pet_type": "Dog", "pet_breed": "German Shepherd", "status": "confirmed"},
        {"user": clients[1], "date": today, "slot": "11:00 AM", "pet_name": "Daisy", "pet_type": "Dog", "pet_breed": "Beagle", "status": "completed"},
        {"user": clients[2], "date": today, "slot": "2:00 PM", "pet_name": "Bruiser", "pet_type": "Dog", "pet_breed": "Chihuahua", "status": "confirmed"},
        {"user": clients[0], "date": today, "slot": "4:00 PM", "pet_name": "T-800", "pet_type": "Cat", "pet_breed": "Sphynx", "status": "pending"},
        
        # Tomorrow's Appointments
        {"user": clients[1], "date": tomorrow, "slot": "10:00 AM", "pet_name": "Baba Yaga", "pet_type": "Cat", "pet_breed": "Russian Blue", "status": "confirmed"},
        {"user": clients[2], "date": tomorrow, "slot": "1:00 PM", "pet_name": "Pinky", "pet_type": "Rabbit", "pet_breed": "Holland Lop", "status": "confirmed"},
        {"user": clients[0], "date": tomorrow, "slot": "3:00 PM", "pet_name": "T-1000", "pet_type": "Dog", "pet_breed": "Husky", "status": "confirmed"},

        # Day 3 Appointments
        {"user": clients[2], "date": day3, "slot": "8:00 AM", "pet_name": "Bruiser", "pet_type": "Dog", "pet_breed": "Chihuahua", "status": "confirmed"},
        {"user": clients[1], "date": day3, "slot": "9:00 AM", "pet_name": "Daisy", "pet_type": "Dog", "pet_breed": "Beagle", "status": "confirmed"},
        {"user": clients[0], "date": day3, "slot": "2:00 PM", "pet_name": "T-800", "pet_type": "Cat", "pet_breed": "Sphynx", "status": "confirmed"},
        {"user": clients[1], "date": day3, "slot": "4:00 PM", "pet_name": "Baba Yaga", "pet_type": "Cat", "pet_breed": "Russian Blue", "status": "confirmed"},

        # Day 4 Appointments
        {"user": clients[0], "date": day4, "slot": "11:00 AM", "pet_name": "Terminator", "pet_type": "Dog", "pet_breed": "German Shepherd", "status": "confirmed"},
        {"user": clients[2], "date": day4, "slot": "12:00 PM", "pet_name": "Pinky", "pet_type": "Rabbit", "pet_breed": "Holland Lop", "status": "confirmed"}
    ]
    
    for bd in bookings_data:
        # Check if booking exists to prevent duplicates
        existing = Booking.query.filter_by(email=bd['user'].email, date=bd['date'], slot=bd['slot']).first()
        if not existing:
            b = Booking(
                service_id=service.id,
                slot=bd['slot'],
                date=bd['date'],
                name=f"{bd['user'].first_name} {bd['user'].last_name}",
                email=bd['user'].email,
                phone=bd['user'].contact,
                pet_name=bd['pet_name'],
                pet_type=bd['pet_type'],
                pet_breed=bd['pet_breed'],
                visit_reason="Routine checkup and vaccination.",
                status=bd['status'],
                user_id=bd['user'].id,
                handled_by="Dr. Veterinarian" if bd['status'] == 'completed' else None
            )
            db.session.add(b)

    db.session.commit()
    print("Mock bookings added.")
    print("✅ Database seeding complete! The dashboard should now look full of data.")
