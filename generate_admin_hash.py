import hashlib
# generate_admin_hash.py

password = input("Enter admin password: ")
print(hashlib.sha256(password.encode()).hexdigest())