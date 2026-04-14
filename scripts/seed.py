import asyncio
import os
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from passlib.context import CryptContext

# Simple script to seed the database with sample data
MONGODB_URI = "mongodb+srv://Vercel-Admin-event_db:5zu9TBoE47XetNE3@event-db.bvfx2ae.mongodb.net/?retryWrites=true&w=majority"
MONGODB_DB = "event_api"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed():
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB]
    
    print("Clearing existing data (Events, Bookings, Reviews)...")
    await db.events.delete_many({})
    await db.bookings.delete_many({})
    await db.reviews.delete_many({})
    
    # Check for/Create user
    user = await db.users.find_one({"email": "jane@example.com"})
    if not user:
        print("Creating sample user Jane Doe...")
        user_doc = {
            "email": "jane@example.com",
            "password_hash": pwd_context.hash("securepassword123"),
            "full_name": "Jane Doe",
            "roles": ["user"],
            "role": "user",
            "is_verified": True,
            "created_at": datetime.now(timezone.utc)
        }
        result = await db.users.insert_one(user_doc)
        user = await db.users.find_one({"_id": result.inserted_id})
        
        # Create profile
        await db.profiles.insert_one({
            "user_id": user["_id"],
            "full_name": "Jane Doe",
            "display_name": "Jane Doe",
            "avatar_url": "https://example.com/avatar.jpg",
            "notifications_enabled": True
        })

    print("Seeding events...")
    events_data = [
        {
            "title": "Art Workshop",
            "imageUrl": "https://images.unsplash.com/photo-1460666819451-e161150e96be",
            "additionalImages": ["https://images.unsplash.com/photo-1513364776144-60967b0f800f"],
            "description": "Painting workshop with professional artists. Learn techniques and create your own masterpiece.",
            "event_start_datetime": datetime.now(timezone.utc) + timedelta(days=10),
            "location_name": "Centre Artisanal, Yaoundé",
            "price": 5000,
            "category": "Art",
            "attendees": 50,
            "is_featured": True
        },
        {
            "title": "Food & Wine Festival",
            "imageUrl": "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3",
            "additionalImages": [],
            "description": "Culinary journey with fine wines and gourmet food from top chefs.",
            "event_start_datetime": datetime.now(timezone.utc) + timedelta(days=20),
            "location_name": "Plage de Kribi, Kribi",
            "price": 15000,
            "category": "Food",
            "attendees": 350,
            "is_featured": False
        },
        {
            "title": "Music Festival 2025",
            "imageUrl": "https://images.unsplash.com/photo-1459749411177-042180ce672c",
            "additionalImages": [],
            "description": "Annual music festival featuring international and local artists.",
            "event_start_datetime": datetime.now(timezone.utc) + timedelta(days=30),
            "location_name": "National Stadium, Douala",
            "price": 10000,
            "category": "Music",
            "attendees": 5000,
            "is_featured": True
        },
        {
            "title": "Comedy Night Live",
            "imageUrl": "https://images.unsplash.com/photo-1527224857830-43a7acc85260",
            "additionalImages": [],
            "description": "Laugh until it hurts with our lineup of top comedians.",
            "event_start_datetime": datetime.now(timezone.utc) + timedelta(days=5),
            "location_name": "Cercle Municipal, Yaoundé",
            "price": 5000,
            "category": "Music",
            "attendees": 120,
            "is_featured": False
        }
    ]
    
    event_results = await db.events.insert_many(events_data)
    print(f"Inserted {len(event_results.inserted_ids)} events.")
    
    event_id = event_results.inserted_ids[0]
    print(f"Creating sample booking for user: {user['email']}...")
    booking = {
        "bookingId": f"bk-{ObjectId()}",
        "userId": user["_id"],
        "eventId": str(event_id),
        "fullName": "Jane Doe",
        "email": "jane@example.com",
        "phoneNumber": "+237612345678",
        "ticketCount": 2,
        "totalPrice": 10000,
        "status": "upcoming"
    }
    await db.bookings.insert_one(booking)
    
    print("Creating sample review...")
    await db.reviews.insert_one({
        "user_id": user["_id"],
        "event_id": event_id,
        "rating": 5,
        "reviewText": "Amazing experience! The instructors were very professional.",
        "created_at": datetime.now(timezone.utc),
        "likes": 12
    })

    print("Seeding complete.")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
