# Ingestion (owner: B)

Airbyte Cloud click-path and non-secret IDs go here (filled in during B4–B6).

- Source: File — dataset name `city_day`, format `csv`, storage HTTPS public web, URL = GitHub raw link of `data/city_day.csv`
- Destination: Snowflake — role `AIRBYTE_ROLE`, warehouse `AIRSIGHT_WH`, database `AIRSIGHT`, default schema `RAW`, user `AIRBYTE_USER`
- Connection: stream `city_day`, **Full refresh | Overwrite**, manual schedule
- Connection ID: _(non-secret; put in local .env as AIRBYTE_CONNECTION_ID)_
