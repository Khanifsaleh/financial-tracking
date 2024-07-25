import pandas as pd
import streamlit as st
import re
from datetime import datetime, timedelta
import pytz
import os
from github import Github
from streamlit import session_state as ss
import calendar

this_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(this_dir, '..'))
db_dir = os.path.join(root_dir, 'db')
data_dir = os.path.join(root_dir, 'data')
db_name = st.secrets["db"]["name"]
db_path = os.path.join(db_dir, db_name)
conn = st.connection('fintrack_db', type='sql')

github = Github(st.secrets["git"]["token"])
repo_owner = 'Khanifsaleh'
repo_name = 'kkk_financial_tracking'
repo = github.get_user(repo_owner).get_repo(repo_name)

css_button_style = """
    button {
        background-color: #FF4B4B;
        color: white;
    }
"""

# def commit_and_push(content, new_content, commit_message):
    
def get_num_days(year_month):
    year, month = year_month.split('-')
    year, month = int(year), int(month)
    return calendar.monthrange(year, month)[1]

def get_color(percentage):
    if percentage <= 70:
        return '#5FA55A'
    elif percentage <= 80:
        return '#F6D51F'
    elif percentage <= 95:
        return '#FA8925'
    else:
        return '#FA5457'
    
def progress_bar(category, budget, expenses):
    percentage_spent = (expenses/budget)*100
    bar_width = 100 if percentage_spent>100 else percentage_spent
    color = get_color(bar_width)
    # font-family: 'Comic Sans MS', cursive;
    progress_html = f"""
    <div style="margin-bottom: 5px;">
        <div style="left: 10px; font-size: 10px;">
                {category} ({format_label(expenses)}/{format_label(budget)})
            </div>
        <div style="position: relative; height: 25px; width: 100%; display: flex; align-items: center;">
            <div style=" position: relative; height: 25px; width: 100%; background-color: #F0F2F6; border-radius: 5px; display: flex; align-items: center;">
                <div style="position: absolute; height: 100%; width: {bar_width}%; background-color: {color}; border-radius: 5px;"></div>
            </div>
            <div style="position: absolute; right: 10px; font-size: 12px; color: black; font-weight:bold">{percentage_spent:.2f}%</div>
        </div>
    </div>
    """
    st.markdown(progress_html, unsafe_allow_html=True)

def update_data_repo(table):
    datapath = os.path.join(data_dir, f'{table}.csv')
    pd_read_sql(f'select * from {table}').to_csv(datapath, index=False)
    with open(datapath, 'rb') as f:
        data_content = f.read()
    content = repo.get_contents(f"data/{table}.csv")
    repo.update_file(
        content.path, 
        f"update {table} table", 
        data_content, content.sha, 
        branch=st.secrets["git"]["BRANCH"]
    )

    with open(db_path, 'rb') as f:
        db_content = f.read()
    content = repo.get_contents(f"db/{db_name}")
    repo.update_file(
        content.path,
        f"update {table} table",
        db_content, content.sha,
        branch=st.secrets["git"]["BRANCH"]
    )

def pd_read_sql(sql_string, columns=None):
    data = conn._instance.execute(sql_string).fetchall()
    df = pd.DataFrame(data)
    if columns:
        df = df[columns]
    return df

def insert_data(table_name, data_dict):
    columns = list(data_dict.keys())
    values = list(data_dict.values())
    sql_string = '''
    INSERT INTO {} {} VALUES {}
    '''.format(
        table_name, '('+ ', '.join(columns) + ')', '('+ ', '.join(['?']*len(columns)) + ')'
    )
    conn._instance.execute(sql_string, tuple(values))

def update_data_by_id(table_name, data_dict, idx):
    set_clause = ', '.join([f"{col} = '{value}'" for col, value in data_dict.items()])
    sql_string = f"UPDATE {table_name} SET {set_clause} WHERE id = {idx}"
    conn._instance.execute(sql_string)
    update_data_repo(table_name)

def update_data(table_name, data_dict, condition=None):
    set_clause = ', '.join([f"{col} = '{value}'" for col, value in data_dict.items()])
    if condition is None:
        sql_string = f"UPDATE {table_name} SET {set_clause}"
    else:
        sql_string = f"UPDATE {table_name} SET {set_clause} WHERE {condition}"
    conn._instance.execute(sql_string)
    update_data_repo(table_name)

def delete_data_by_id(table_name, idx_list):
    idx_list = [str(i) for i in idx_list]
    sql_string = f"DELETE FROM {table_name} WHERE id IN ({', '.join(idx_list)})"
    conn._instance.execute(sql_string)
    update_data_repo(table_name)

def format_rupiah(amount):
    rupiah = "Rp {:,.2f}".format(amount)
    return rupiah

def format_label(num):
    if num < 1_000_000:
        return f"{num/1_000:.0f}K"
    else:
        return f"{num/1_000_000:.1f}M"
    
def add_timenow(date):
    timenow = datetime.now() + timedelta(hours=7)
    hms = timedelta(hours=timenow.hour, minutes=timenow.minute, seconds=timenow.second)
    return (pd.to_datetime(date) + hms).strftime("%Y-%m-%d %H:%M:%S")

def clean_text(s):
    s = s.lower().strip()
    s = re.sub('\s+', ' ', s)
    return re.sub('[^_a-z\s0-9]', '', s)

def on_change_data(df, table_name):
    if ss.category_edited['edited_rows']:
        edited_rows = ss.category_edited['edited_rows']

        row_idx = list(edited_rows.keys())[0]
        rows = df.iloc[int(row_idx)]
        
        data_dict = edited_rows[row_idx]
        idx = rows['id']
        update_data_by_id(table_name, data_dict, idx)

    if ss.expenses_edited['deleted_rows']:
        deleted_rows = ss.expenses_edited['deleted_rows']
        delete_data_by_id('expenses', df.iloc[deleted_rows]['id'].tolist())
