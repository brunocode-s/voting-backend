# from eth_account import Account
# account = Account.create()
# print(f"Address: {account.address}")
# print(f"Private Key: {account.key.hex()}")

from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())