import asyncio
import os
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Simple script to seed the database with sample data
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "event_api")

async def seed():
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB]
    
    print("Clearing existing data...")
    await db.events.delete_many({})
    await db.bookings.delete_many({})
    await db.reviews.delete_many({})
    
    print("Seeding events...")
    events = [
        {
            "title": "Art Workshop",
            "imageUrl": "https://images.unsplash.com/photo-1460666819451-e161150e96be",
            "additionalImages": ["https://images.unsplash.com/photo-1513364776144-60967b0f800f"],
            "description": "Painting workshop with professional artists. Learn techniques and create your own masterpiece.",
            "event_start_datetime": datetime.utcnow() + timedelta(days=10),
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
            "event_start_datetime": datetime.utcnow() + timedelta(days=20),
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
            "event_start_datetime": datetime.utcnow() + timedelta(days=30),
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
            "event_start_datetime": datetime.utcnow() + timedelta(days=5),
            "location_name": "Cercle Municipal, Yaoundé",
            "price": 5000,
            "category": "Music", # Categories from spec: Art, Music, Food
            "attendees": 120,
            "is_featured": False
        }
    ]
    
    result = await db.events.insert_many(events)
    print(f"Inserted {len(result.inserted_ids)} events.")
    
    # Simple bio for first user if exists
    user = await db.users.find_one({})
    if user:
        print(f"Creating sample booking for user: {user['email']}...")
        event_id = result.inserted_ids[0]
        booking = {
            "bookingId": f"bk-{ObjectId()}",
            "userId": user["_id"],
            "eventId": event_id,
            "fullName": user.get("full_name", "Jane Doe"),
            "email": user["email"],
            "phoneNumber": "+237612345678",
            "ticketCount": 2,
            "totalPrice": 10000,
            "status": "upcoming"
        }
        await db.bookings.insert_one(booking)
        print("Sample booking created.")

    print("Seeding complete.")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
