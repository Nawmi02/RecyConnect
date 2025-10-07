from django.db import migrations

CREATE_SQL = """
PRAGMA foreign_keys=OFF;

CREATE TABLE IF NOT EXISTS "Marketplace_marketorder" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "order_no" varchar(20) NOT NULL UNIQUE,
    "buyer_id" integer NOT NULL REFERENCES "User_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    "collector_id" integer NOT NULL REFERENCES "User_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    "marketplace_id" integer NOT NULL REFERENCES "Marketplace_marketplace" ("id") DEFERRABLE INITIALLY DEFERRED,
    "product_name" varchar(120) NOT NULL,
    "weight_kg" numeric NOT NULL,
    "unit_price" numeric NOT NULL,
    "total_price" numeric NOT NULL,
    "status" varchar(10) NOT NULL,
    "created_at" datetime NOT NULL,
    "updated_at" datetime NOT NULL
);

-- Helpful indexes (optional)
CREATE INDEX IF NOT EXISTS "marketplace_buyer_idx" ON "Marketplace_marketorder" ("buyer_id");
CREATE INDEX IF NOT EXISTS "marketplace_collector_idx" ON "Marketplace_marketorder" ("collector_id");

PRAGMA foreign_keys=ON;
"""

DROP_SQL = """
DROP TABLE IF EXISTS "Marketplace_marketorder";
"""

class Migration(migrations.Migration):

    dependencies = [
        ('Marketplace', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(CREATE_SQL, reverse_sql=DROP_SQL),
    ]
