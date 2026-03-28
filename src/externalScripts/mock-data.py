import uuid
import random
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

fake = Faker()

def random_issue_and_due():
    # issue_date in past 6 months
    issue = fake.date_between(start_date='-6M', end_date='today')
    # due between 15 and 60 days after issue
    due = issue + timedelta(days=random.randint(15, 60))
    return issue, due

def derive_status(due_date, paid_date):
    today = datetime.today().date()
    if paid_date:
        return "Paid"
    elif due_date < today:
        return "Overdue"
    elif (due_date - today).days <= 7:
        return "Upcoming Due"
    else:
        return "Open"

def generate_mock_invoices(n=200):
    records = []
    for _ in range(n):
        issue_date, due_date = random_issue_and_due()
        # 70% chance unpaid, 30% paid
        if random.random() < 0.3:
            paid_date = fake.date_between(start_date=issue_date, end_date=due_date + timedelta(days=30))
        else:
            paid_date = None

        status = derive_status(due_date, paid_date)
        record = {
            "invoice_id": f"INV-{uuid.uuid4().hex[:8].upper()}",
            "customer_id": f"CUST-{fake.random_uppercase_letter()}{fake.random_number(digits=4)}",
            "customer_name": fake.company(),
            "issue_date": issue_date,
            "due_date": due_date,
            "amount": round(random.uniform(100, 10000), 2),
            "currency": random.choice(["USD", "CZK"]),
            "status": status,
            "paid_date": paid_date
        }
        records.append(record)

    return pd.DataFrame(records)

if __name__ == "__main__":
    df = generate_mock_invoices(200)
    # Save to CSV for bq load or further manipulation
    df.to_csv("mock_invoices.csv", index=False)
    print("Generated mock_invoices.csv with 200 rows.")
