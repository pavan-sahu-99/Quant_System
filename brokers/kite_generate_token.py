from kiteconnect import KiteConnect
import pandas as pd

path = r"config\\kite_api.txt"
def gen_access_token():
    key = open(path ,"r").read().split()
    kite = KiteConnect(api_key=key[0])
    print(kite.login_url())
    request_token = input("Enter the request_token: ").strip()
    data = kite.generate_session(request_token, api_secret= key[1])
    access_token = data["access_token"]
    print(access_token)
    with open(path ,"r") as f:
        lines = f.readlines()

    with open(path,"w") as f:
        f.write(lines[0])  # API key
        f.write(lines[1])  # API secret
        
        # Write new access token
        f.write(f"{access_token}\n")

if __name__ == "__main__":
    gen_access_token()