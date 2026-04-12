Request URL
http://localhost:8000/api/v1/subscriptions/create
Request Method
POST
Status Code

{
"plan_id": "9ed7ae7c-6cb6-43be-bc84-f9cea22d1dbb",
"billing_cycle": "monthly",
"seat_count": 10
}

{
"success": false,
"message": "Company already has an active subscription",
"error_code": "SUBSCRIPTION_EXISTS"
}
