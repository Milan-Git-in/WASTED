from django.http import JsonResponse
from .Supabase import supabase
import json
import os
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
from supabase import create_client
from .auth import hash_password, verify_password, generate_jwt

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase config missing")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_storage(request):
    try:
        buckets = supabase.storage.list_buckets()
        return JsonResponse({"status": "ok", "buckets": buckets})
    except Exception as e:
        return JsonResponse({"status":"error", "success":True,"error": str(e)}, status=500)




@csrf_exempt
def register(request):
    if request.method != "POST":
        return JsonResponse({"success":False,"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        # Basic validation
        if not username or len(username) < 2:
            return JsonResponse({"success":False,"error": "Username must be at least 2 characters."}, status=400)
        if not email or "@" not in email:
            return JsonResponse({"success":False,"error": "Invalid email."}, status=400)
        if not password or len(password) < 6:
            return JsonResponse({"success":False,"error": "Password too short."}, status=400)

        # Check if user exists
        existing = supabase.table("users").select("id").eq("email", email).execute()
        if existing.data:
            return JsonResponse({"success":False,"error": "Email already registered."}, status=409)

        # Hash password
        hashed_pw = hash_password(password)

        # Save user
        result = supabase.table("users").insert({
            "username": username,
            "email": email,
            "password": hashed_pw
        }).execute()

        user = result.data[0]
        token = generate_jwt({"id": user["id"], "email": user["email"]})

        return JsonResponse({"success": True ,"message": "Registered", "token": token}, status=201)

    except Exception as e:
        return JsonResponse({"success":False,"error": str(e)}, status=500)


@csrf_exempt
def login(request):
    if request.method != "POST":
        return JsonResponse({"success":False,"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return JsonResponse({"success":False,"error": "Email and password required"}, status=400)

        result = supabase.table("users").select("*").eq("email", email).single().execute()
        user = result.data

        if not user or not verify_password(password, user["password"]):
            return JsonResponse({"success":False,"error": "Invalid credentials"}, status=401)

        token = generate_jwt({"id": user["id"], "email": user["email"]})

        return JsonResponse({"success":True,"message": "Logged in", "token": token}, status=200)

    except Exception as e:
        return JsonResponse({"success":False,"error": str(e)}, status=500)





@csrf_exempt
def list_items(request):
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "error": "Only POST allowed"
        }, status=405)

    try:
        data = json.loads(request.body)
        email = data.get("email")
        item_name = data.get("itemName")
        raw_has_bid = data.get("hasStartingBid")
        starting_bid = data.get("startingBid")


        if isinstance(raw_has_bid, bool):
            has_starting_bid = raw_has_bid
        elif isinstance(raw_has_bid, str):
            has_starting_bid = raw_has_bid.lower() == "true"
        else:
            return JsonResponse({
                "success": False,
                "error": "'hasStartingBid' must be a boolean or         'true'/'false' string"
                }, status=400)

        # Validate email
        if not email or "@" not in email:
            return JsonResponse({
                "success": False,
                "error": "Invalid email"
            }, status=400)

        # Validate item name
        if not item_name or not isinstance(item_name, str) or len(item_name.strip()) == 0:
            return JsonResponse({
                "success": False,
                "error": "Item name is required"
            }, status=400)

        # Validate hasStartingBid (must be boolean)

        if not isinstance(has_starting_bid, bool):
            return JsonResponse({
                "success": False,
                "error": "'hasStartingBid' must be a boolean"
            }, status=400)

        # Validation logic based on checkbox
        if has_starting_bid:
            if starting_bid is None:
                return JsonResponse({
                    "success": False,
                    "error": "Starting bid is required when enabled",
                }, status=400)
            try:
                starting_bid = float(starting_bid)
                if starting_bid < 0:
                    return JsonResponse({
                        "success": False,
                        "error": "Starting bid must be ≥ 0"
                    }, status=400)
            except (TypeError, ValueError):
                return JsonResponse({
                    "success": False,
                    "error": "Invalid starting bid value"
                }, status=400)
        else:
            if starting_bid is not None:
                return JsonResponse({
                    "success": False,
                    "error": "Starting bid must be empty when disabled"
                }, status=400)

        # Insert into Supabase (assuming table "listings" exists)
        insert_data = {
            "email": email,
            "item_name": item_name,
            "has_starting_bid": has_starting_bid,
            "starting_bid": starting_bid
        }

        response = supabase.table("listings").insert(insert_data).execute()

        if response.get("error"):
            return JsonResponse({
                "success": False,
                "error": response["error"]["message"]
            }, status=500)

        return JsonResponse({
            "success": True,
            "message": "Item listed successfully"
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


@csrf_exempt
def get_bids(request):
    if request.method != "GET":
        return JsonResponse({"success": False, "error": "Only GET allowed"}, status=405)

    try:
        bids_response = supabase.table("bids").select("*").execute()
        bids = bids_response.data or []

        if not bids:
            return JsonResponse({
                "success": True,
                "data": [{
                    "id": "No bids",
                    "amount": 0,
                    "name": "Unknown",  # Use 'name' here to match frontend
                    "status": "Pending",
                    "email": "Nobids@gmail.com"
                }]
            })

        # Rename 'item_name' to 'name' for frontend
        renamed_bids = []
        for bid in bids:
            renamed_bids.append({
                "id": bid.get("id"),
                "email": bid.get("email"),
                "amount": bid.get("amount"),
                "status": bid.get("status"),
                "name": bid.get("item_name", "Unknown")  # rename here
            })

        return JsonResponse({"success": True, "data": renamed_bids}, safe=False)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
def available_lists(request):
    if request.method != "GET":
        return JsonResponse({"success": False, "error": "Only GET allowed"}, status=405)

    try:
        response = supabase.table("listings").select("*").execute()
        listings = response.data or []

        if not listings:
            return JsonResponse({
                "success": True,
                "data": [{
                    "itemName": "No available products",
                    "hasStartingBid": True,
                    "startingBid": 100000
                }]
            })

        # Format listings
        formatted = [{
            "itemName": item.get("item_name"),
            "hasStartingBid": item.get("has_starting_bid", False),
            "startingBid": item.get("starting_bid")
        } for item in listings]

        return JsonResponse({"success": True, "data": formatted}, safe=False)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)



@csrf_exempt
def place_bids(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        amount = data.get("amount")
        email = data.get("email")
        item_name = data.get("item")

        if not all([amount, email, item_name]):
            return JsonResponse({"success": False, "error": "Missing required fields"}, status=400)

        # Get listing by item name
        listing_resp = supabase.table("listings").select("*").eq("item_name", item_name).single().execute()
        listing = listing_resp.data

        if not listing:
            return JsonResponse({"success": False, "error": "Invalid item"}, status=400)

        has_starting_bid = listing.get("has_starting_bid", False)
        starting_bid = listing.get("starting_bid", None)

        if has_starting_bid and starting_bid is not None and amount < starting_bid:
            return JsonResponse({
                "success": False,
                "error": f"Bid must be at least {starting_bid}"
            }, status=400)

        # Insert bid
        insert_resp = supabase.table("bids").insert({
            "email": email,
            "amount": amount,
            "status": "Pending",  # or 'Submitted'
            "item_name": item_name
        }).execute()

        if insert_resp.get("error"):
            return JsonResponse({"success": False, "error": "Could not place bid"}, status=500)

        return JsonResponse({"success": True, "message": "Bid placed successfully"})

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
