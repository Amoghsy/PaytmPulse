import sys
import logging
from decimal import Decimal
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.models import Merchant, Product, Inventory, Customer, Transaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("paytm_pulse.validate")


def validate_database():
    logger.info("Running Paytm Pulse Database Validation Suite...")
    errors = []

    with SessionLocal() as session:
        # Check 1: Orphan Products
        orphan_products = session.query(Product).filter(~Product.merchant_id.in_(session.query(Merchant.id))).all()
        if orphan_products:
            errors.append(f"Found {len(orphan_products)} orphan products with invalid merchant_id.")

        # Check 2: Orphan Customers
        orphan_customers = session.query(Customer).filter(~Customer.merchant_id.in_(session.query(Merchant.id))).all()
        if orphan_customers:
            errors.append(f"Found {len(orphan_customers)} orphan customers with invalid merchant_id.")

        # Check 3: Orphan Transactions
        orphan_tx_merchant = session.query(Transaction).filter(~Transaction.merchant_id.in_(session.query(Merchant.id))).all()
        if orphan_tx_merchant:
            errors.append(f"Found {len(orphan_tx_merchant)} orphan transactions with invalid merchant_id.")

        orphan_tx_product = session.query(Transaction).filter(~Transaction.product_id.in_(session.query(Product.id))).all()
        if orphan_tx_product:
            errors.append(f"Found {len(orphan_tx_product)} orphan transactions with invalid product_id.")

        orphan_tx_customer = session.query(Transaction).filter(
            Transaction.customer_id.isnot(None),
            ~Transaction.customer_id.in_(session.query(Customer.id))
        ).all()
        if orphan_tx_customer:
            errors.append(f"Found {len(orphan_tx_customer)} orphan transactions with invalid customer_id.")

        # Check 4: Negative Inventory
        negative_inventory = session.query(Inventory).filter(Inventory.current_stock < 0).all()
        if negative_inventory:
            errors.append(f"Found {len(negative_inventory)} inventory records with negative current_stock.")

        # Check 5: Transaction Amount Calculation
        bad_tx_amounts = []
        for tx in session.query(Transaction).all():
            expected = Decimal(str(tx.quantity)) * tx.unit_price
            if abs(tx.amount - expected) > Decimal("0.01"):
                bad_tx_amounts.append(tx.id)
        if bad_tx_amounts:
            errors.append(f"Found {len(bad_tx_amounts)} transactions where amount != quantity * unit_price.")

        # Check 6: Customer Spend Metrics
        mismatched_customers = []
        for cust in session.query(Customer).all():
            cust_txs = session.query(Transaction).filter_by(customer_id=cust.id).all()
            actual_tx_count = len(cust_txs)
            actual_total_spend = sum((tx.amount for tx in cust_txs), Decimal("0.00"))

            # Skip checking scen_d override if any
            if cust.purchase_count != actual_tx_count:
                mismatched_customers.append((cust.id, "purchase_count mismatch"))
            elif abs(cust.total_spend - actual_total_spend) > Decimal("0.01"):
                mismatched_customers.append((cust.id, "total_spend mismatch"))

        if mismatched_customers:
            errors.append(f"Found {len(mismatched_customers)} customer records with mismatched purchase metrics.")

        # Check 7: Merchant Cross-Relationship Integrity
        cross_rel_mismatches = []
        for tx in session.query(Transaction).all():
            prod = session.get(Product, tx.product_id)
            if prod and prod.merchant_id != tx.merchant_id:
                cross_rel_mismatches.append(tx.id)
        if cross_rel_mismatches:
            errors.append(f"Found {len(cross_rel_mismatches)} transactions where product merchant_id != transaction merchant_id.")

    if errors:
        logger.error("❌ Database validation failed with the following errors:")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("✅ Database validation successful.")
        return True


if __name__ == "__main__":
    validate_database()
