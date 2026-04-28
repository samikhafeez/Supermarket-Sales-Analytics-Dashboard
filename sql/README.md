# Supermarket Sales Analytics Dashboard

## Overview
This project analyses supermarket sales data using SQL, Python, and Streamlit. It focuses on business intelligence tasks such as identifying top-performing branches, product lines, payment trends, and customer behaviour.

## Objectives
- Clean and preprocess supermarket sales data
- Store data in a SQL database
- Write business-focused SQL queries
- Build an interactive dashboard for key sales insights

## Tools and Technologies
- Python
- Pandas
- SQLite
- SQL
- Streamlit
- Matplotlib

## Dataset
The dataset contains supermarket transaction records including product line, branch, city, payment method, quantity, revenue, and ratings.

## Features
- Total revenue KPI
- Average customer rating
- Top-performing branch
- Revenue by branch
- Revenue by product line
- Payment method usage
- Sales by hour

## How to Run
1. Install dependencies:
   `pip install -r requirements.txt`

2. Load the dataset into SQLite:
   `python src/load_data.py`

3. Run the dashboard:
   `streamlit run app/dashboard.py`

## Reflection
This project improved my SQL querying, data cleaning, KPI design, and dashboard development skills. It also helped me understand how business data can be transformed into actionable insights.