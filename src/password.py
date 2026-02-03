import hashlib
import random

def generate_random_salt(salt_length: int) -> bytes:
  lwc = ''.join([chr(i) for i in range(ord('a'), ord('z') + 1)])
  upc = ''.join([chr(i) for i in range(ord('A'), ord('Z') + 1)])
  nmb = ''.join([chr(i) for i in range(ord('0'), ord('9') + 1)])
  tot = lwc + upc + nmb
  
  salt = "".join(random.choice(tot) for i in range(salt_length))
  
  return bytes(salt, "utf-8")

def salt(password: bytes, salt: bytes) -> tuple:
   pwd = bytearray(password)
   arr = bytearray(salt)
   salted = pwd + arr

   salted = bytes(salted)

   return (salted, salt)

def hash(password: bytes) -> str:
  return hashlib.sha256(password).hexdigest()
