# from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
# from pydantic import BaseModel
# import json
# import httpx
# import hashlib
# import hmac
# import os
# from typing import Optional
# import asyncio
# from datetime import datetime

# app = FastAPI(title="Webhook Testing with Svix Play")

# # Configuration
# SVIX_PLAY_ENDPOINT = "https://play.svix.com/in/e_kmfpbH0D9z3gzdBcprasF5TH8RJ/"  # Replace with your Svix Play URL
# LOCAL_WEBHOOK_SECRET = "whsec_ST3RNC+uLTH67J3dveHQsI1lrZm14hpI"

# # Pydantic models for webhook payloads
# class ClerkUserData(BaseModel):
#     id: str
#     email_addresses: list
#     first_name: Optional[str] = None
#     last_name: Optional[str] = None
#     primary_email_address_id: Optional[str] = None

# class ClerkWebhookPayload(BaseModel):
#     type: str
#     data: ClerkUserData

# class SvixPlayForwardRequest(BaseModel):
#     svix_play_url: str
#     webhook_payload: dict

# # Utility functions
# def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
#     """Verify webhook signature from Clerk/Svix"""
#     if secret.startswith('whsec_'):
#         secret = secret[6:]
    
#     expected_signature = hmac.new(
#         secret.encode('utf-8'),
#         payload,
#         hashlib.sha256
#     ).hexdigest()
    
#     return hmac.compare_digest(signature, expected_signature)

# def extract_svix_signature(signature_header: str) -> Optional[str]:
#     """Extract signature from Svix signature header format"""
#     try:
#         sig_parts = signature_header.split(",")
#         for part in sig_parts:
#             if part.startswith("v1="):
#                 return part[3:]  # Remove "v1=" prefix
#         return None
#     except Exception:
#         return None

# # Main webhook endpoint that will receive forwarded webhooks
# @app.post("/webhooks/clerk/user")
# async def clerk_user_webhook(request: Request):
#     """Main webhook endpoint to handle Clerk user events"""
    
#     print("=== WEBHOOK RECEIVED ===")
#     print("Headers:", dict(request.headers))
    
#     # Get the raw payload
#     payload = await request.body()
#     print("Raw payload:", payload.decode('utf-8'))
    
#     # Get signature for verification (optional in development)
#     signature = request.headers.get("svix-signature")
    
#     # For development, you might skip signature verification
#     # In production, always verify signatures
#     if signature and LOCAL_WEBHOOK_SECRET:
#         actual_signature = extract_svix_signature(signature)
#         if actual_signature and not verify_webhook_signature(payload, actual_signature, LOCAL_WEBHOOK_SECRET):
#             print("❌ Signature verification failed")
#             raise HTTPException(status_code=401, detail="Invalid signature")
#         print("✅ Signature verified")
    
#     try:
#         # Parse the webhook data
#         webhook_data = json.loads(payload.decode('utf-8'))
        
#         # Handle different event types
#         event_type = webhook_data.get("type")
#         print(f"Event type: {event_type}")
        
#         if event_type == "user.created":
#             await handle_user_created(webhook_data.get("data", {}))
#         elif event_type == "user.updated":
#             await handle_user_updated(webhook_data.get("data", {}))
#         elif event_type == "user.deleted":
#             await handle_user_deleted(webhook_data.get("data", {}))
#         else:
#             print(f"Unhandled event type: {event_type}")
        
#         print("✅ Webhook processed successfully")
#         return {"status": "success", "event_type": event_type}
        
#     except json.JSONDecodeError as e:
#         print(f"❌ Invalid JSON: {e}")
#         raise HTTPException(status_code=400, detail="Invalid JSON payload")
#     except Exception as e:
#         print(f"❌ Error processing webhook: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# async def handle_user_created(user_data: dict):
#     """Handle user.created event"""
#     user_id = user_data.get("id")
    
#     # Get primary email
#     email_addresses = user_data.get("email_addresses", [])
#     primary_email = None
    
#     for email_obj in email_addresses:
#         if email_obj.get("id") == user_data.get("primary_email_address_id"):
#             primary_email = email_obj.get("email_address")
#             break
    
#     print(f"👤 New user created:")
#     print(f"   - ID: {user_id}")
#     print(f"   - Email: {primary_email}")
#     print(f"   - Name: {user_data.get('first_name')} {user_data.get('last_name')}")
    
#     # TODO: Insert into your database
#     # db_user = User(
#     #     id=user_id,
#     #     email=primary_email,
#     #     first_name=user_data.get("first_name"),
#     #     last_name=user_data.get("last_name")
#     # )
#     # db.add(db_user)
#     # db.commit()
    
#     print("💾 User saved to database (simulated)")

# async def handle_user_updated(user_data: dict):
#     """Handle user.updated event"""
#     user_id = user_data.get("id")
#     print(f"📝 User updated: {user_id}")
    
#     # TODO: Update user in your database

# async def handle_user_deleted(user_data: dict):
#     """Handle user.deleted event"""
#     user_id = user_data.get("id")
#     print(f"🗑️ User deleted: {user_id}")
    
#     # TODO: Delete or deactivate user in your database

# # Endpoint to manually forward webhooks from Svix Play
# @app.post("/webhooks/forward-from-svix-play")
# async def forward_from_svix_play(forward_request: SvixPlayForwardRequest):
#     """Forward a webhook payload from Svix Play to local endpoint"""
    
#     try:
#         # Forward the webhook to our local endpoint
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 "http://localhost:8000/webhooks/clerk/user",
#                 json=forward_request.webhook_payload,
#                 headers={"Content-Type": "application/json"}
#             )
        
#         return {
#             "message": "Webhook forwarded successfully",
#             "response_status": response.status_code,
#             "response_body": response.json() if response.status_code == 200 else response.text
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to forward webhook: {str(e)}")

# # Test endpoints
# @app.post("/test/simulate-user-created")
# async def simulate_user_created():
#     """Simulate a user.created webhook for testing"""
    
#     fake_payload = {
#         "type": "user.created",
#         "data": {
#             "id": f"user_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
#             "email_addresses": [
#                 {
#                     "id": "email_test123",
#                     "email_address": "test@example.com"
#                 }
#             ],
#             "primary_email_address_id": "email_test123",
#             "first_name": "Test",
#             "last_name": "User",
#             "created_at": datetime.utcnow().isoformat()
#         }
#     }
    
#     # Send to our webhook endpoint
#     async with httpx.AsyncClient() as client:
#         response = await client.post(
#             "http://localhost:8000/webhooks/clerk/user",
#             json=fake_payload
#         )
    
#     return {
#         "message": "Test webhook sent",
#         "payload": fake_payload,
#         "response": response.json() if response.status_code == 200 else response.text
#     }

# @app.post("/test/send-to-svix-play")
# async def send_test_to_svix_play():
#     """Send a test webhook to Svix Play endpoint"""
    
#     if not SVIX_PLAY_ENDPOINT:
#         raise HTTPException(status_code=400, detail="Svix Play endpoint not configured")
    
#     test_payload = {
#         "type": "user.created",
#         "data": {
#             "id": f"user_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
#             "email_addresses": [
#                 {
#                     "id": "email_test123",
#                     "email_address": "test@example.com"
#                 }
#             ],
#             "primary_email_address_id": "email_test123",
#             "first_name": "Test",
#             "last_name": "User from FastAPI"
#         }
#     }
    
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 SVIX_PLAY_ENDPOINT,
#                 json=test_payload,
#                 headers={"Content-Type": "application/json"}
#             )
        
#         return {
#             "message": "Test webhook sent to Svix Play",
#             "svix_response_status": response.status_code,
#             "payload": test_payload
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to send to Svix Play: {str(e)}")

# @app.get("/")
# async def root():
#     return {
#         "message": "FastAPI Webhook Testing with Svix Play",
#         "endpoints": {
#             "webhook_receiver": "/webhooks/clerk/user",
#             "forward_from_svix": "/webhooks/forward-from-svix-play",
#             "test_local": "/test/simulate-user-created",
#             "test_svix_play": "/test/send-to-svix-play"
#         },
#         "svix_play_url": SVIX_PLAY_ENDPOINT if SVIX_PLAY_ENDPOINT else "Not configured"
#     }

# @app.get("/health")
# async def health():
#     return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# # Development helper to show recent webhook logs
# webhook_logs = []

# @app.middleware("http")
# async def log_webhooks(request: Request, call_next):
#     if request.url.path.startswith("/webhooks/"):
#         # Log webhook requests
#         body = await request.body()
#         webhook_logs.append({
#             "timestamp": datetime.utcnow().isoformat(),
#             "method": request.method,
#             "path": request.url.path,
#             "headers": dict(request.headers),
#             "body": body.decode('utf-8') if body else None
#         })
        
#         # Keep only last 10 logs
#         if len(webhook_logs) > 10:
#             webhook_logs.pop(0)
    
#     response = await call_next(request)
#     return response

# @app.get("/webhooks/logs")
# async def get_webhook_logs():
#     """View recent webhook requests for debugging"""
#     return {
#         "recent_webhooks": webhook_logs,
#         "count": len(webhook_logs)
#     }

# if __name__ == "__main__":
#     import uvicorn
#     print("🚀 Starting FastAPI with Svix Play integration...")
#     print(f"📡 Svix Play endpoint: {SVIX_PLAY_ENDPOINT}")
#     print("🔗 Local webhook endpoint: http://localhost:8000/webhooks/clerk/user")
#     uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)