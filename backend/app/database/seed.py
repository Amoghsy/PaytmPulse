import os
import random
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from app.database.connection import engine, SessionLocal
from app.models import (
    Base,
    Merchant, MerchantCategory,
    Product, Inventory,
    Customer, Transaction, PaymentMethod,
    BusinessEvent, EventType, EventSeverity,
    Recommendation, RecommendationType, RecommendationStatus,
    Action, ActionType, ActionStatus, Outcome
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("paytm_pulse.seed")

RANDOM_SEED = 42


def reset_database(session: Session):
    logger.info("Clearing existing development data...")
    session.query(Outcome).delete()
    session.query(Action).delete()
    session.query(Recommendation).delete()
    session.query(BusinessEvent).delete()
    session.query(Transaction).delete()
    session.query(Customer).delete()
    session.query(Inventory).delete()
    session.query(Product).delete()
    session.query(Merchant).delete()
    session.commit()
    logger.info("Database reset complete.")


def seed_data(clear_existing: bool = True):
    random.seed(RANDOM_SEED)
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=30)

    # Make sure tables exist first
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        existing_count = session.query(Merchant).count()
        if not clear_existing and existing_count > 0:
            logger.info(f"Database already populated with {existing_count} merchants. Skipping re-seed.")
            return

        reset_database(session)

        logger.info("Seeding merchants...")
        merchants_data = [
            ("Ravi Kumar", "Ravi General Store", MerchantCategory.KIRANA, "Bengaluru", "Kannada", "9876543210"),
            ("Sharma Ji", "Sharma Kirana & Provisions", MerchantCategory.KIRANA, "Delhi", "Hindi", "9876543211"),
            ("Dr. Ananya Roy", "Roy Pharmacy & Healthcare", MerchantCategory.PHARMACY, "Kolkata", "Bengali", "9876543212"),
            ("Gurpreet Singh", "Punjab Rasoi Dhaba", MerchantCategory.RESTAURANT, "Chandigarh", "Punjabi", "9876543213"),
            ("Rajesh Patel", "Metro Electronics & Mobiles", MerchantCategory.ELECTRONICS, "Ahmedabad", "Gujarati", "9876543214"),
            ("Priya Sundaram", "Style Studio Boutique", MerchantCategory.CLOTHING, "Chennai", "Tamil", "9876543215"),
            ("Suresh Verma", "Verma Supermart", MerchantCategory.KIRANA, "Jaipur", "Hindi", "9876543216"),
            ("Amitabh Das", "Das Sweet House", MerchantCategory.RESTAURANT, "Lucknow", "Hindi", "9876543217"),
            ("Kavita Menon", "Menon Health Pharmacy", MerchantCategory.PHARMACY, "Kochi", "Malayalam", "9876543218"),
            ("Vikram Rao", "Rao Digital Appliances", MerchantCategory.ELECTRONICS, "Hyderabad", "Telugu", "9876543219"),
        ]

        merchants = []
        for name, shop_name, category, location, language, phone in merchants_data:
            merchant = Merchant(
                name=name,
                shop_name=shop_name,
                category=category,
                location=location,
                language=language,
                phone=phone
            )
            session.add(merchant)
            merchants.append(merchant)
        
        session.commit()
        logger.info(f"Created {len(merchants)} merchants.")

        # Product Templates per Category
        product_templates = {
            MerchantCategory.KIRANA: [
                ("Aashirvaad Atta 5kg", "Staples", 260.0, 220.0, "ITC Ltd"),
                ("Fortune Sunflower Oil 1L", "Staples", 145.0, 125.0, "Adani Wilmar"),
                ("Amul Butter 500g", "Dairy", 275.0, 245.0, "Amul GCMMF"),
                ("Amul Taaza Milk 1L", "Dairy", 54.0, 48.0, "Amul GCMMF"),
                ("Tata Salt 1kg", "Staples", 28.0, 22.0, "Tata Consumer"),
                ("Maggi 2-Min Noodles 280g", "Packaged Food", 48.0, 40.0, "Nestle India"),
                ("Surf Excel Easy Wash 1kg", "Household", 140.0, 115.0, "Hindustan Unilever"),
                ("Colgate Strong Toothpaste 200g", "Personal Care", 110.0, 90.0, "Colgate-Palmolive"),
                ("Parle-G Biscuit 250g", "Snacks", 25.0, 20.0, "Parle Products"),
                ("Good Day Cashew Biscuits", "Snacks", 35.0, 28.0, "Britannia"),
                ("Cadbury Dairy Milk 50g", "Confectionery", 40.0, 32.0, "Mondelez"),
                ("Lays Magic Masala Chips", "Snacks", 20.0, 15.0, "PepsiCo"),
            ],
            MerchantCategory.PHARMACY: [
                ("Paracetamol 650mg 15s", "Medicines", 32.0, 20.0, "Cipla Ltd"),
                ("Azithromycin 500mg 3s", "Medicines", 118.0, 85.0, "Sun Pharma"),
                ("Pantocid D SR 10s", "Medicines", 145.0, 105.0, "Sun Pharma"),
                ("Volini Pain Relief Gel 50g", "OTC", 165.0, 130.0, "Sun Pharma"),
                ("Dettol Antiseptic 250ml", "Hygiene", 125.0, 98.0, "Reckitt Benckiser"),
                ("Revital H Capsules 30s", "Supplements", 330.0, 260.0, "Sun Pharma"),
                ("Thermometer Digital", "Devices", 220.0, 150.0, "Omron"),
                ("N95 Mask Pack of 5", "Safety", 150.0, 90.0, "3M India"),
                ("Horlicks Health Drink 500g", "Nutrition", 265.0, 225.0, "Hindustan Unilever"),
                ("ORSL Electrolyte Drink 200ml", "OTC", 35.0, 26.0, "Johnson & Johnson"),
                ("Vicks Vaporub 50g", "OTC", 110.0, 85.0, "Procter & Gamble"),
                ("Band-Aid Washproof 20s", "First Aid", 45.0, 32.0, "Johnson & Johnson"),
            ],
            MerchantCategory.RESTAURANT: [
                ("Paneer Butter Masala", "Main Course", 240.0, 110.0, "In-House"),
                ("Butter Naan", "Breads", 45.0, 15.0, "In-House"),
                ("Chicken Biryani (Full)", "Main Course", 290.0, 140.0, "In-House"),
                ("Veg Thali Combo", "Combos", 180.0, 80.0, "In-House"),
                ("Dal Makhani", "Main Course", 210.0, 90.0, "In-House"),
                ("Masala Dosa", "South Indian", 90.0, 35.0, "In-House"),
                ("Gulab Jamun (2 pcs)", "Desserts", 60.0, 20.0, "In-House"),
                ("Cold Coffee with Ice Cream", "Beverages", 120.0, 45.0, "In-House"),
                ("Lassi Special 300ml", "Beverages", 70.0, 25.0, "In-House"),
                ("Organic Green Tea Cup", "Beverages", 50.0, 12.0, "Tea Box"),
                ("Garlic Naan", "Breads", 55.0, 18.0, "In-House"),
                ("Tandoori Roti", "Breads", 20.0, 6.0, "In-House"),
            ],
            MerchantCategory.ELECTRONICS: [
                ("Boat Airdopes 141 Wireless", "Audio", 1299.0, 950.0, "Imagine Marketing"),
                ("Fastrack Smartwatch Reflex", "Wearables", 2499.0, 1850.0, "Titan Co"),
                ("SanDisk 64GB Pen Drive", "Storage", 499.0, 360.0, "Western Digital"),
                ("Type-C Fast Charging Cable", "Accessories", 299.0, 120.0, "Mi India"),
                ("Mi 20000mAh Power Bank", "Accessories", 1899.0, 1450.0, "Mi India"),
                ("Logitech Wireless Mouse", "Peripherals", 699.0, 510.0, "Logitech"),
                ("JBL GO 3 Portable Speaker", "Audio", 2999.0, 2200.0, "Harman International"),
                ("Tempered Glass Screen Guard", "Accessories", 199.0, 30.0, "Local Supplier"),
                ("Mobile Back Cover Premium", "Accessories", 299.0, 60.0, "Local Supplier"),
                ("Realme Earbuds TechLife", "Audio", 899.0, 650.0, "Realme India"),
                ("Samsung 25W Wall Charger", "Accessories", 1299.0, 920.0, "Samsung"),
                ("Keyboard USB Ergonomic", "Peripherals", 599.0, 420.0, "Zebronics"),
            ],
            MerchantCategory.CLOTHING: [
                ("Men Cotton Casual Shirt", "Menswear", 899.0, 480.0, "Raymond Ltd"),
                ("Women Floral Print Kurti", "Womenswear", 750.0, 380.0, "Biba Apparels"),
                ("Slim Fit Blue Jeans", "Bottomwear", 1499.0, 820.0, "Levis India"),
                ("Cotton Polo T-Shirt", "Menswear", 499.0, 240.0, "Allen Solly"),
                ("Silk Printed Dupatta", "Womenswear", 399.0, 180.0, "FabIndia"),
                ("Track Pants Gymwear", "Activewear", 699.0, 360.0, "Puma India"),
                ("Ethnic Saree Banarasi", "Ethnic", 3499.0, 1900.0, "Craftsvilla"),
                ("Kids Denim Jacket", "Kidswear", 850.0, 450.0, "FirstCry"),
                ("Casual Socks Pack of 3", "Accessories", 199.0, 80.0, "Jockey India"),
                ("Leather Belt Classic", "Accessories", 599.0, 270.0, "Woodland"),
                ("Formal Trousers Black", "Menswear", 1199.0, 620.0, "Park Avenue"),
                ("Cotton Nightdress Comfort", "Sleepwear", 550.0, 280.0, "Zivame"),
            ]
        }

        first_names = ["Ramesh", "Suresh", "Priya", "Ankit", "Deepak", "Neha", "Vikram", "Sunita", "Pooja", "Rahul", "Arjun", "Kavita", "Sanjay", "Meena", "Manish", "Anita", "Rajesh", "Swati", "Nitin", "Bhavna"]
        last_names = ["Sharma", "Verma", "Patel", "Singh", "Kumar", "Gupta", "Rao", "Joshi", "Nair", "Das", "Reddy", "Mehta", "Bhasin", "Agarwal", "Deshmukh", "Chowdhury", "Kulkarni", "Chawla", "Sen", "Bhat"]

        products = []
        customers = []

        logger.info("Seeding products & inventory for merchants...")
        for m in merchants:
            templates = product_templates.get(m.category, product_templates[MerchantCategory.KIRANA])
            for idx, (p_name, p_cat, p_price, p_cost, p_supp) in enumerate(templates):
                stock = random.randint(25, 120)
                reorder = random.randint(10, 25)
                max_stock = stock + random.randint(50, 150)
                avg_sales = round(random.uniform(2.0, 15.0), 2)

                product = Product(
                    merchant_id=m.id,
                    name=p_name,
                    category=p_cat,
                    price=Decimal(str(p_price)),
                    cost_price=Decimal(str(p_cost)),
                    current_stock=stock,
                    reorder_level=reorder,
                    supplier=p_supp,
                    average_daily_sales=Decimal(str(avg_sales)),
                    is_active=True
                )
                session.add(product)
                products.append(product)
                session.flush()

                inventory = Inventory(
                    product_id=product.id,
                    current_stock=stock,
                    reorder_level=reorder,
                    maximum_stock=max_stock,
                    last_restocked_at=now - timedelta(days=random.randint(2, 20))
                )
                session.add(inventory)

            for c_idx in range(random.randint(35, 45)):
                c_name = f"{random.choice(first_names)} {random.choice(last_names)}"
                c_phone = f"91{random.randint(7000000000, 9999999999)}"
                customer = Customer(
                    merchant_id=m.id,
                    name=c_name,
                    phone=c_phone,
                    total_spend=Decimal("0.00"),
                    purchase_count=0,
                    last_purchase_at=None,
                    average_purchase_interval=Decimal(str(round(random.uniform(3.0, 14.0), 2)))
                )
                session.add(customer)
                customers.append(customer)

        session.commit()
        logger.info(f"Created {len(products)} products and {len(customers)} customers.")

        logger.info("Generating realistic time-series transaction history (30 days)...")
        transactions = []

        m1 = merchants[0]
        m2 = merchants[1]
        m3 = merchants[2]
        m4 = merchants[3]

        m1_products = [p for p in products if p.merchant_id == m1.id]
        m2_products = [p for p in products if p.merchant_id == m2.id]
        m3_products = [p for p in products if p.merchant_id == m3.id]
        m4_products = [p for p in products if p.merchant_id == m4.id]

        m1_customers = [c for c in customers if c.merchant_id == m1.id]

        scen_a_product = m1_products[0]  # Demand Spike Target
        scen_b_product = m2_products[2]  # Sales Decline Target
        scen_c_product = m3_products[0]  # Stockout Risk Target
        scen_d_customer = m1_customers[4] # Customer Risk Target

        for day_offset in range(30):
            current_day = start_date + timedelta(days=day_offset)
            is_recent = day_offset >= 23

            for m in merchants:
                m_prods = [p for p in products if p.merchant_id == m.id]
                m_custs = [c for c in customers if c.merchant_id == m.id]
                if not m_prods:
                    continue

                daily_tx_count = random.randint(10, 22)
                for _ in range(daily_tx_count):
                    prod = random.choice(m_prods)
                    cust = random.choice(m_custs) if random.random() > 0.15 else None
                    
                    if prod.id == scen_a_product.id and is_recent and day_offset >= 25:
                        qty = random.randint(5, 10)
                    elif prod.id == scen_b_product.id and is_recent:
                        if random.random() > 0.70:
                            continue
                        qty = 1
                    else:
                        qty = random.randint(1, 4)

                    if cust and cust.id == scen_d_customer.id and day_offset > 2:
                        continue

                    unit_p = prod.price
                    amt = Decimal(str(qty)) * unit_p

                    hour = random.choice([10, 11, 12, 17, 18, 19, 20, 21]) if random.random() > 0.3 else random.randint(8, 22)
                    minute = random.randint(0, 59)
                    tx_time = current_day.replace(hour=hour, minute=minute, second=random.randint(0, 59))

                    method = random.choice([PaymentMethod.UPI, PaymentMethod.UPI, PaymentMethod.CASH, PaymentMethod.CARD])

                    tx = Transaction(
                        merchant_id=m.id,
                        product_id=prod.id,
                        customer_id=cust.id if cust else None,
                        quantity=qty,
                        unit_price=unit_p,
                        amount=amt,
                        payment_method=method,
                        transaction_timestamp=tx_time
                    )
                    transactions.append(tx)

        scen_c_product.current_stock = 12
        scen_c_product.reorder_level = 50
        scen_c_inventory = session.query(Inventory).filter_by(product_id=scen_c_product.id).first()
        if scen_c_inventory:
            scen_c_inventory.current_stock = 12
            scen_c_inventory.reorder_level = 50

        session.add_all(transactions)
        session.commit()
        logger.info(f"Seeded {len(transactions)} transactions.")

        logger.info("Updating aggregated customer stats and inventory metrics...")
        
        all_customers = session.query(Customer).all()
        for cust in all_customers:
            cust_txs = session.query(Transaction).filter_by(customer_id=cust.id).order_by(Transaction.transaction_timestamp.asc()).all()
            if cust_txs:
                cust.purchase_count = len(cust_txs)
                cust.total_spend = sum((tx.amount for tx in cust_txs), Decimal("0.00"))
                cust.last_purchase_at = cust_txs[-1].transaction_timestamp
                
                if len(cust_txs) > 1:
                    first_tx = cust_txs[0].transaction_timestamp
                    last_tx = cust_txs[-1].transaction_timestamp
                    days_diff = (last_tx - first_tx).days
                    if days_diff > 0:
                        cust.average_purchase_interval = Decimal(str(round(days_diff / (len(cust_txs) - 1), 2)))
                    else:
                        cust.average_purchase_interval = Decimal("1.00")
                else:
                    cust.average_purchase_interval = Decimal("7.00")

        scen_d_customer.last_purchase_at = now - timedelta(days=35)
        scen_d_customer.average_purchase_interval = Decimal("7.00")

        session.commit()
        logger.info("Data seeding completed successfully!")


if __name__ == "__main__":
    seed_data(clear_existing=True)
