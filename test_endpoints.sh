#!/bin/bash

BASE_URL="http://localhost:8000"
USERNAME="curl_user_$(date +%s)"
PASSWORD="password123"
PLATE="NL-$(shuf -i 10-99 -n 1)-$(shuf -i 10-99 -n 1)"

echo "---------------------------------------------------"
echo "1. Registering User: $USERNAME"
curl -s -X POST "$BASE_URL/register" \
     -H "Content-Type: application/json" \
     -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\", \"name\": \"Curl Tester\"}" | jq .

echo -e "\n---------------------------------------------------"
echo "2. Logging In"
LOGIN_RES=$(curl -s -X POST "$BASE_URL/login" \
     -H "Content-Type: application/json" \
     -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

TOKEN=$(echo $LOGIN_RES | jq -r .session_token)
echo "Token: $TOKEN"

if [ "$TOKEN" == "null" ]; then
    echo "Login failed. Exiting."
    exit 1
fi

AUTH_HEADER="Authorization: $TOKEN"

echo -e "\n---------------------------------------------------"
echo "3. Creating Vehicle: $PLATE"
VEHICLE_RES=$(curl -s -X POST "$BASE_URL/vehicles" \
     -H "$AUTH_HEADER" \
     -H "Content-Type: application/json" \
     -d "{\"user_id\": \"$USERNAME\", \"license_plate\": \"$PLATE\", \"make\": \"Ford\", \"model\": \"Focus\", \"color\": \"Blue\", \"year\": 2020}")
echo $VEHICLE_RES | jq .
VEHICLE_ID=$(echo $VEHICLE_RES | jq -r .id)

echo -e "\n---------------------------------------------------"
echo "4. Get User Vehicles"
curl -s -X GET "$BASE_URL/vehicles" \
     -H "$AUTH_HEADER" | jq .

echo -e "\n---------------------------------------------------"
echo "5. Get Parking Lots"
LOTS_RES=$(curl -s -X GET "$BASE_URL/parking-lots/")
echo $LOTS_RES | jq '.[0:1]' # Show just the first one to save space
LOT_ID=$(echo $LOTS_RES | jq -r 'keys[0]') # Get first key (parking lot id)
echo "Using Parking Lot ID: $LOT_ID"

echo -e "\n---------------------------------------------------"
echo "6. Create Reservation"
START_TIME=$(date -u +"%Y-%m-%dT%H:%M")
END_TIME=$(date -u -d "+2 hours" +"%Y-%m-%dT%H:%M")

RESERVATION_RES=$(curl -s -X POST "$BASE_URL/reservations/" \
     -H "$AUTH_HEADER" \
     -H "Content-Type: application/json" \
     -d "{\"vehicle_id\": \"$VEHICLE_ID\", \"parking_lot_id\": \"$LOT_ID\", \"start_time\": \"$START_TIME\", \"end_time\": \"$END_TIME\"}")
echo $RESERVATION_RES | jq .
RESERVATION_ID=$(echo $RESERVATION_RES | jq -r .reservation.id)

echo -e "\n---------------------------------------------------"
echo "7. Start Parking Session"
curl -s -X POST "$BASE_URL/parking-lots/$LOT_ID/sessions/start" \
     -H "$AUTH_HEADER" \
     -H "Content-Type: application/json" \
     -d "{\"licenseplate\": \"$PLATE\"}" | jq .

echo -e "\n---------------------------------------------------"
echo "8. Stop Parking Session (After 1 sec delay)"
sleep 1
SESSION_RES=$(curl -s -X PUT "$BASE_URL/parking-lots/$LOT_ID/sessions/stop" \
     -H "$AUTH_HEADER" \
     -H "Content-Type: application/json" \
     -d "{\"licenseplate\": \"$PLATE\"}")
echo $SESSION_RES | jq .
SESSION_ID=$(echo $SESSION_RES | jq -r .id) # Note: ID might be in keys or body depending on impl

echo -e "\n---------------------------------------------------"
echo "9. Make Payment"
# Assuming we can pay for the session we just stopped
# Need to construct a payment object. The backend expects specific structure.
# Since the session might have cost 0 (short duration), we force a small amount for test.
PAYMENT_DATA="{\"amount\": 5.00, \"session_id\": \"$SESSION_ID\", \"parking_lot_id\": \"$LOT_ID\", \"t_data\": {\"amount\": 5.00, \"date\": \"$START_TIME\", \"method\": \"creditcard\", \"issuer\": \"VISA\", \"bank\": \"TestBank\"}}"

curl -s -X POST "$BASE_URL/payments" \
     -H "$AUTH_HEADER" \
     -H "Content-Type: application/json" \
     -d "$PAYMENT_DATA" | jq .

echo -e "\n---------------------------------------------------"
echo "10. Delete Reservation"
curl -s -X DELETE "$BASE_URL/reservations/$RESERVATION_ID" \
     -H "$AUTH_HEADER" | jq .

echo -e "\n---------------------------------------------------"
echo "11. Delete Vehicle"
curl -s -X DELETE "$BASE_URL/vehicles/$PLATE" \
     -H "$AUTH_HEADER" | jq .

echo -e "\n---------------------------------------------------"
echo "Tests Completed."
