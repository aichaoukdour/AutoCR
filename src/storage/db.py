from pymongo import MongoClient

client = MongoClient("mongodb://root:rootpass@localhost:27017/")
db = client["mydb"]
collection = db["videos"]  # ou une autre collection selon ton besoin
