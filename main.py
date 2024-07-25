import streamlit as st
import os

from src.utils import *
from src.expenses import Expenses
from src.incomes import Incomes
from src.receivables import Receivables

def get_unique_months():
    query = """
        SELECT 
            DISTINCT strftime('%Y-%m', date) AS MonthYear 
        FROM expenses
        ORDER BY MonthYear DESC;
    """
    return [l[0] for l in conn._instance.execute(query).fetchall()]

def get_categories():
    query = "select distinct(category_name) from categories"
    return sorted([l[0] for l in conn._instance.execute(query).fetchall()])

def get_assets_name():
    query = "select distinct(affected_asset) from incomes"
    return [l[0] for l in conn._instance.execute(query).fetchall()]

def main():
    categories = get_categories()
    assets = get_assets_name()
    months = get_unique_months()
    
    _exp = Expenses(categories=categories, assets=assets, months=months)
    _inc = Incomes(assets=assets, months=months)
    _rec = Receivables(assets=assets)
    tab_expense, tab_income, tab_rec = st.tabs(["Expenses", "Incomes", "Receivables"])
    with tab_expense:
        _exp.run()
    with tab_income:
        _inc.run()
    with tab_rec:
        _rec.run()

if __name__ == '__main__':
    main()