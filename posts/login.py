from django.contrib.auth import authenticate


user = authenticate(username="new_user", password="secure_pass123")
if user is not None:
    print("Authentication successful!")
else:
    print("Invalid credentials.")

