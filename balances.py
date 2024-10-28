import os

BALANCE_FILE = "balances.txt"

# Read balances from the text file
def read_balances():
    balances = {}
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, "r") as f:
            for line in f:
                name, money = line.strip().split()
                balances[name] = int(money)
    return balances

# Write balances to the text file
def write_balances(balances):
    with open(BALANCE_FILE, "w") as f:
        for name, money in balances.items():
            f.write(f"{name} {money}\n")
