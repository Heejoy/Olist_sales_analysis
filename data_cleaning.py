import pandas as pd
import numpy as np
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "Data" / "Raw"
PROCESSED = BASE / "Data" / "Cleaned_data"
PROCESSED.mkdir(parents=True, exist_ok=True)

customers = pd.read_excel(RAW / "olist_customers_dataset.xlsx")
orders = pd.read_excel(
        RAW / "olist_orders_dataset.xlsx",
        parse_dates= [
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date"
            ],
)
order_items = pd.read_excel(RAW / "olist_order_items_dataset.xlsx")
order_payments = pd.read_excel(RAW / "olist_order_payments_dataset.xlsx")
order_reviews = pd.read_excel(RAW / "olist_order_reviews_dataset.xlsx")
products = pd.read_excel(RAW / "olist_products_dataset.xlsx")
sellers = pd.read_excel(RAW / "olist_sellers_dataset.xlsx")
category_translation = pd.read_excel(RAW / "product_category_name_translation.xlsx")

# ----------------------------------------------------------------------
# Fix typo 
# ----------------------------------------------------------------------
products = products.rename(columns={
    "product_name_lenght": "product_name_length",
    "product_description_lenght": "product_description_length"
})
# print(products.columns.tolist())

# Count real customers
n_customer_ids = customers["customer_id"].nunique()
n_real_customers = customers["customer_unique_id"].nunique()

print(f"customer_id (per order):   {n_customer_ids:,}")      # 99,441
print(f"customer_unique_id (real): {n_real_customers:,}")    # 96,096

# ----------------------------------------------------------------------
# Map state to full names
# ----------------------------------------------------------------------
state_mapping = {
    "SP": "Sao Paulo",
    "SC": "Santa Catarina",
    "MG": "Minas Gerais",
    "PR": "Parana",
    "RJ": "Rio de Janeiro",
    "RS": "Rio Grande do Sul",
    "PA": "Para",
    "GO": "Goias",
    "ES": "Espirito Santo",
    "BA": "Bahia",
    "MA": "Maranhao",
    "MS": "Mato Grosso do Sul",
    "CE": "Ceara",
    "DF": "Distrito Federal",
    "RN": "Rio Grande do Norte",
    "PE": "Pernambuco",
    "MT": "Mato Grosso",
    "AM": "Amazonas",
    "AP": "Amapa",
    "AL": "Alagoas",
    "RO": "Rondonia",
    "PB": "Paraiba", 
    "TO": "Tocantins", 
    "PI": "Piaui",
    "AC": "Acre", 
    "SE": "Sergipe", 
    "RR": "Roraima",
}

customers["customer_state"] = customers["customer_state"].map(state_mapping)
sellers["seller_state"] = sellers["seller_state"].map(state_mapping)

print(customers["customer_state"].value_counts().head())

# Transate product category names to English
category_dict = category_translation.set_index("product_category_name")["product_category_name_english"]

products.insert(
    2, "product_category_name_english", products["product_category_name"].map(category_dict)
)

# a Portuguese category can be missing from the translation table entirely
missing_mask = products["product_category_name"].notna() & products["product_category_name_english"].isna()
print(f"Products whose category has no English translation: {missing_mask.sum()}")
products.loc[missing_mask, "product_category_name"].value_counts()

manual_category_translation = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_and_food_prep",
}
products["product_category_name_english"] = products["product_category_name_english"].fillna(
    products["product_category_name"].map(manual_category_translation)
)

still_missing = products["product_category_name"].notna() & products["product_category_name_english"].isna()
print(f"Still missing after manual fix: {still_missing.sum()}")

no_category_at_all = products["product_category_name"].isna().sum()
print(f"Products with no category at all (left as NaN, handle as 'Unknown' downstream): {no_category_at_all}")

# ----------------------------------------------------------------------
# Clean the orders table
# ----------------------------------------------------------------------
# orders that have no payment record
orders_ids = set(orders["order_id"])
payment_ids = set(order_payments["order_id"])
orphan_orders = orders_ids - payment_ids
print(f"Orders with no matching payment row: {len(orphan_orders)}")           # expect 1

orders_cleaned = orders[orders["order_id"].isin(payment_ids)].copy()
print("orders_cleaned shape:", orders_cleaned.shape)                          # expect (99440, 8)

print(orders_cleaned["order_status"].value_counts())

# keep delivered orders only
order_delivered = orders_cleaned[orders_cleaned["order_status"] == "delivered"].copy()
print("delivered orders:", order_delivered.shape)     

# ----------------------------------------------------------------------
# Re-key orders to the real customer (customer_unique_id)
# ----------------------------------------------------------------------
customers_id_map = customers[["customer_id", "customer_unique_id"]]

orders_customer_unique_id = customers_id_map.merge(order_delivered, how="left", on="customer_id")
orders_customer_unique_id = orders_customer_unique_id.drop(columns="customer_id")
orders_customer_unique_id = orders_customer_unique_id.dropna(subset=["order_id"])

n_active_customers = orders_customer_unique_id["customer_unique_id"].nunique()
print(f"Customers with at least one delivered order: {n_active_customers:,}")  # expect 93,357
print(f"Customers with zero delivered orders: {n_real_customers - n_active_customers:,}")  # expect 2,739
print(orders_customer_unique_id.head())

# 8. Save cleaned tables
customers.to_excel(PROCESSED / "customers_clean.xlsx", index=False)
sellers.to_excel(PROCESSED / "sellers_clean.xlsx", index=False)
products.to_excel(PROCESSED / "products_clean.xlsx", index=False)
orders_customer_unique_id.to_excel(PROCESSED / "orders_customer_unique_id.xlsx", index=False)
order_payments.to_excel(PROCESSED / "order_payments.xlsx", index=False)
order_items.to_excel(PROCESSED / "order_items_clean.xlsx", index=False)

print("Saved cleaned tables to:", PROCESSED.resolve())
for f in sorted(PROCESSED.glob("*.xlsx")):
    print(" -", f.name)