import pandas as pd
import json

df = pd.read_csv("russia-cities-cleaned.csv")

result = {
    region: [
        {"name": row.Name, "longitude": row.Longitude, "latitude": row.Latitude}
        for row in group.itertuples()
    ]
    for region, group in df.groupby("Region", sort=False)
}

with open("regions.json", "w", encoding="utf-8") as filp:
    json.dump(result, filp, ensure_ascii=False, indent=4)