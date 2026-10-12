import pandas as pd

df = pd.read_csv('cities-in-russia-cleaned.csv')

with open('purge.txt', encoding='utf-8') as f:
    purge = {line.strip() for line in f if line.strip()}

df = df[~df['Federal subject'].isin(purge)]

df.to_csv('cities-in-russia-cleaned-purged.csv', index=False)