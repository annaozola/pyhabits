import requests
import uuid
import os
from auth_service import auth
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

def _headers():
    if not auth.id_token:
        raise Exception("Not authenticated")
    return {
        "Authorization": f"Bearer {auth.id_token}"
    }

def fetch_all_habits():
    uid = auth.local_id
    url = f"{BASE_URL}/users/{uid}/habits"
    
    resp = requests.get(url, headers=_headers())
    if resp.status_code == 404:
        return {}
        
    data = resp.json()
    if "error" in data:
        raise Exception(data["error"]["message"])
        
    habits = {}
    if "documents" in data:
        for doc in data["documents"]:
            doc_id = doc["name"].split("/")[-1]
            fields = doc.get("fields", {})
            
            name = fields.get("name", {}).get("stringValue", "Unknown")
            completions_map = fields.get("completions", {}).get("mapValue", {}).get("fields", {})
            
            parsed_completions = {}
            for date_str, val_obj in completions_map.items():
                if "integerValue" in val_obj:
                    parsed_completions[date_str] = int(val_obj["integerValue"])
                elif "doubleValue" in val_obj:
                    parsed_completions[date_str] = float(val_obj["doubleValue"])
                    
            habits[name] = {
                "_id": doc_id, # Store for syncing back
                "completion": parsed_completions,
                "measurement": None,
                "category": "General",
                "archived": False,
                "icon": None
            }
    return habits

def push_all_habits(habits):
    uid = auth.local_id
    
    for name, data in habits.items():
        doc_id = data.get("_id")
        if not doc_id:
            doc_id = str(uuid.uuid4())
            data["_id"] = doc_id
            
        url = f"{BASE_URL}/users/{uid}/habits/{doc_id}"
        
        # Build completions map
        fields = {}
        for date_str, amount in data.get("completion", {}).items():
            if isinstance(amount, int):
                fields[date_str] = {"integerValue": str(amount)}
            else:
                fields[date_str] = {"doubleValue": float(amount)}
                
        payload = {
            "fields": {
                "name": {"stringValue": name},
                "completions": {
                    "mapValue": {
                        "fields": fields
                    }
                }
            }
        }
        
        requests.patch(url, headers=_headers(), json=payload)

def sync_with_firestore(local_habits):
    print("      [~] Fetching cloud data...")
    cloud_habits = fetch_all_habits()
    
    merged = False
    
    for name, cloud_data in cloud_habits.items():
        if name not in local_habits:
            local_habits[name] = cloud_data
            merged = True
        else:
            local_data = local_habits[name]
            # Merge completions
            for date_str, amount in cloud_data.get("completion", {}).items():
                if date_str not in local_data.get("completion", {}):
                    local_data.setdefault("completion", {})[date_str] = amount
                    merged = True
            if "_id" not in local_data and "_id" in cloud_data:
                local_data["_id"] = cloud_data["_id"]
                merged = True
    
    print("      [~] Pushing merged data to cloud...")
    push_all_habits(local_habits)
    
    return merged
