import requests

# Define access tokens mapped to business manager labels
ACCESS_TOKENS = {
    'BM1': 'EAAItf7ZBw0cgBO4YZChbgtpZBXRqkl22newE5PgCxgzJAoW1FciO5ydpbPZCikOY1SvZAcBvJIKVpE6AczSURqv6deMCWEF8XjQupW1TUadsAu4MmmoJ0sZAIzR2kZCMQ9xlwE13xVelJD6uNm7HLuupASeZAnJPfmtZAHRd5ZCc0DKr7dHGRCJloSB0wmd2k3aEIg',
    'fabian_adaccounts': 'EAAQWoXoAnN0BOz2XSXdJwoOxZCG6S8NyIJA7PLlVP4AMROLEsU4BMTItRu5uj81G2ZBWsT66gQz3kQRrIRQQsLL6HzGu1d2yYZB539zo5F24ZAj2SINZCFpZCjBlWwwy2SXcsdhu3DyLlDHCSE9ZA9ZAmqFIa6F1ImNaqgVp7ZAquUXXh9YpYmeduqh1URxFDQJkI',
    'BM3': 'EAAf5KSuCsZBsBO9Jp7TbXopwT55BsRm7jzCKMt3SnkBZCINHmJqgCrTOKc0nBtxrAb1XvY61uhQ0NuPQJOnJQTd7ub5TloiVsgj8Xtg1bMQupu0vdC8vqHkwGUOmMfmUdQKGoLW8bkUhgY4fV6IRxvZAZA1NPt80Ka1AsQROb0FwneQQEy6KswLqK2SBFMTX1wZDZD',
    'BM4': 'EAAN0eLeKC1YBO8eoCZAZBWidwssqPgGls1Md99eNvyZC6QJzJ3JwPBZC2nkSsAuPtHz72i7W9TpH8KZAxyQZAcZA4W1yoTnPQXBEwQhHxm4jnCFobqklDsAvtSy5SgnVtvUPmTCiIYDMVD1uqy7OHcsGhG6EZBVA552ucPEhXxazwZCBnz1FmiPewW8yjze1CxsqyJ7GBNtx4xz1CInpL'
}

# Ad accounts to exclude
EXCLUDE_IDS = ['act_1079103783395840', 'act_418878090721644']

# Storage for the filtered results
filtered_accounts = {}

# Loop over each token and fetch ad accounts
for label, token in ACCESS_TOKENS.items():
    url = f'https://graph.facebook.com/v19.0/me/adaccounts?access_token={token}'
    try:
        response = requests.get(url)
        data = response.json()
        filtered = [acc['id'] for acc in data.get('data', []) if acc.get('id') not in EXCLUDE_IDS]
        filtered_accounts[label] = filtered
        print(f"{label}: {len(filtered)} accounts retrieved.")
    except Exception as e:
        print(f"Error fetching accounts for {label}: {e}")
        filtered_accounts[label] = []

# Save to ad_account_ids.py
with open('ad_account_ids.py', 'w') as f:
    for label, ids in filtered_accounts.items():
        f.write(f"{label} = {ids}\n")

print("✅ ad_account_ids.py updated successfully.")
