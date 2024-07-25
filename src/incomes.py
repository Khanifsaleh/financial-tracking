import sys
import os
import pandas as pd
import streamlit as st
import altair as alt
from streamlit_extras.stylable_container import stylable_container
import streamlit.components.v1 as components
from streamlit import session_state as ss

this_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(this_dir)
from utils import *

st.markdown("""
    <style>
        .center_align {
            text-align: center;
        }
        .header_text {
            font-size: 30px;
            font-weight: bold;
        }
        .indian_color {
            color: #FF4B4B;
        }
        .vertical_center {
                margin: auto;
                width: 50%;
        }
    </style>
""", unsafe_allow_html=True)

class Incomes:
    def __init__(self, **kwargs):
        self.assets = kwargs.get('assets')
        self.months = kwargs.get('months')

    def load_current_asset(self):
        q = """
            SELECT 
                COALESCE(incomes.affected_asset, expenses.affected_asset, receivables.affected_asset) AS affected_asset,
                COALESCE(total_income, 0) - COALESCE(total_expense, 0) - COALESCE(total_receivable, 0) AS current_asset
            FROM 
                (SELECT affected_asset, SUM(amount) AS total_income
                FROM incomes
                GROUP BY affected_asset) incomes
            LEFT JOIN 
                (SELECT affected_asset, SUM(total_amount) AS total_expense
                FROM expenses
                GROUP BY affected_asset) expenses
            ON incomes.affected_asset = expenses.affected_asset
            LEFT JOIN 
                (SELECT affected_asset, SUM(amount) AS total_receivable
                FROM receivables
                GROUP BY affected_asset) receivables
            ON COALESCE(incomes.affected_asset, expenses.affected_asset) = receivables.affected_asset
            LEFT JOIN 
                (SELECT DISTINCT affected_asset FROM
                (SELECT affected_asset FROM incomes
                UNION
                SELECT affected_asset FROM expenses
                UNION
                SELECT affected_asset FROM receivables) all_assets
                ) all_assets
            ON COALESCE(incomes.affected_asset, expenses.affected_asset, receivables.affected_asset) = all_assets.affected_asset;
        """
        df = pd_read_sql(q)
        df = df[df['affected_asset'].isin(self.assets)]
        with st.expander("Filter Assets for In Cash"):
            selected_assets = st.multiselect(
                'Select Assets', 
                df['affected_asset'].unique().tolist(), 
                default = ['bca udin', 'cash konita', 'cash udin', 'cimb konita', 'cimb udin', 'gopay udin', 
                        'koin shopeepay', 'mandiri konita', 'shopee pay udin'
                        ]
            )
        st.markdown(
            f'''
                <p class="header_text" style="float:left;">Current Asset :&nbsp;&nbsp;</p><p class="header_text indian_color">{format_rupiah(df['current_asset'].sum())}</p>
                <p style="float:left;">In Cash :&nbsp;&nbsp;</p> <p class="indian_color">{format_rupiah((df[df['affected_asset'].isin(selected_assets)])['current_asset'].sum())}</p>
            ''', 
            unsafe_allow_html=True)
        # st.write("In Cash: {}".format(
            
        # ))
        st.dataframe(df, use_container_width=True, height=300)
        

    def get_asset_consumtion(self):
        q = """
            SELECT 
                strftime('%Y-%m', date) as month_year,
                affected_asset, sum(total_amount) as amount
            FROM expenses e 
            WHERE category not like '%asset%'
            GROUP BY 
                strftime('%Y-%m', date),
                affected_asset 
        """
        df = pd_read_sql(q)
        return df
        
    def push_new_assets(self):
        assets_name = clean_text(ss['assets_name'])
        assets_name_desc = clean_text(ss['assets_name_desc'])
        if assets_name == '':
            components.html("<script>alert('Asset_name is required!')</script>", height=0, width=0)
        if assets_name not in self.assets:
            category = "initial"
        else:
            category = "topup"
        data_dict = {
            'date' : add_timenow(ss['new_assets_transaction_date']),
            'description': assets_name_desc,
            'category' : category,
            'amount' : ss['new_assets_amount'],
            'affected_asset': assets_name
        }
        insert_data('incomes', data_dict)
    
    @st.experimental_dialog("Asset Details")
    def new_or_topup_asset(self, mode):
        if mode == 'top up':
            # st.text_input("Assets Name", max_chars=25, key='assets_name')
            st.selectbox('Assets Name', self.assets, key='assets_name')
        elif mode == 'new asset':
            st.text_input("Assets Name", max_chars=25, key='assets_name')
        st.text_input("Description", max_chars=25, key='assets_name_desc')
        st.number_input("Assets Amount", min_value=1, value=1000, step=100, key='new_assets_amount')
        st.date_input("Transaction Date", key='new_assets_transaction_date', max_value=datetime.now()+timedelta(hours=7))
        if st.button("Submit"):
            self.push_new_assets()
            update_data_repo('incomes')
            st.rerun()

    def push_transfer_asset(self):
        transfer_amount = int(ss['transfer_amount'])
        transfer_asset_from = ss['transfer_asset_from']
        transfer_asset_to = ss['transfer_asset_to']
        
        data_dict_from = {
            'date' : add_timenow(datetime.now()),
            'item_name': f"transfer to {transfer_asset_to}",
            'category' : "transfer_asset",
            'total_amount' : transfer_amount,
            'affected_asset': transfer_asset_from
        }

        data_dict_to = {
            'date' : add_timenow(datetime.now()),
            'description': f"received from {transfer_asset_from}",
            'category' : "received",
            'amount' : transfer_amount,
            'affected_asset': transfer_asset_to
        }
        
        insert_data('expenses', data_dict_from)
        insert_data('incomes', data_dict_to)

    @st.experimental_dialog("Transfer Asset")
    def transfer_asset(self):
        st.selectbox('Transfer from', self.assets, key='transfer_asset_from')
        st.selectbox('Transfer asset to', self.assets, key='transfer_asset_to')
        st.number_input(
            'Transfer amount', 
            min_value=1, 
            key='transfer_amount'
        )
        if st.button("Submit"):
            self.push_transfer_asset()
            update_data_repo('expenses')
            update_data_repo('incomes')
            st.rerun()
    
    def asset_action(self):
        col1, col2, col3, _ = st.columns([0.9,0.7,1,3])
        with col1:
            with stylable_container(
                "asset_action_button",
                css_styles=css_button_style,
            ):
                if st.button("New Asset"):
                    self.new_or_topup_asset('new asset')

        with col2:
            with stylable_container(
                "asset_action_button",
                css_styles=css_button_style,
            ):
                if st.button("Top Up"):
                    self.new_or_topup_asset('top up')
            
        with col3:
            with stylable_container(
                "asset_action_button",
                css_styles=css_button_style,
            ):
                if st.button("Transfer"):
                    self.transfer_asset()

    def get_incomes_history(self):
        q = "select date,  description, amount, affected_asset from incomes where category='topup'"
        df = pd_read_sql(q)
        df['date'] = pd.to_datetime(df['date'], format='mixed')
        df = df.sort_values('date').reset_index(drop=True)
        df['month_year'] = df['date'].map(lambda x: x.strftime("%Y-%m"))
        return df
        
    def in_out_save(self, df_out, df_in):
        df_out = df_out.groupby('month_year').agg(out_amount=('amount', 'sum')).reset_index()
        df_in = df_in.groupby('month_year').agg(in_amount=('amount', 'sum')).reset_index()
        df = pd.merge(df_out, df_in)
        df['saving'] = df['in_amount'] - df['out_amount']
        st.markdown(
                    f'<p class="header_text indian_color">Saving Summary</p>', 
                    unsafe_allow_html=True
                )
        st.dataframe(df, use_container_width=True)

    def get_history_asset_amount(self):
        st.markdown(
            '<p class="header_text indian_color">History Asset Amount</p>', unsafe_allow_html=True)
        def get_data_per_month(month):
            sql_exp = f"""
                SELECT 
                    strftime('%Y-%m-%d', date) as dateday,
                    SUM(total_amount) as total_amount
                FROM 
                    expenses
                WHERE 
                    strftime('%Y-%m', date) = '{month}'
                GROUP BY 
                    dateday;
            """
            df_exp = pd_read_sql(sql_exp)
            df_exp['total_amount'] = df_exp['total_amount'] * -1
            sql_inc = f"""
                SELECT 
                    strftime('%Y-%m-%d', date) as dateday,
                    SUM(amount) as total_amount
                FROM 
                    incomes
                WHERE 
                    strftime('%Y-%m', date) = '{month}'
                GROUP BY 
                    dateday;
            """
            df_inc = pd_read_sql(sql_inc)
            sql_receivable = f"""
                select 
                    strftime('%Y-%m-%d', date) as dateday,
                    SUM(amount) as total_amount
                from 
                    receivables
                where
                    strftime('%Y-%m', date) = '{month}'
                    and
                    affected_asset in ({', '.join([f"'{a}'" for a in self.assets])})
                GROUP BY 
                    dateday;
            """
            df_rec = pd_read_sql(sql_receivable)
            if len(df_rec)>0:
                df_rec['total_amount'] = df_rec['total_amount'] * -1

            df = pd.concat([df_exp, df_inc, df_rec])
            df = df.groupby('dateday')[['total_amount']].sum().reset_index()
            df['dateday'] = pd.to_datetime(df['dateday'])
            df = df.sort_values('dateday').reset_index(drop=True)
            return int(df['total_amount'].sum())
        
        date_range = pd.date_range(start='2024-04', end=datetime.today(), freq='MS')
        df = pd.DataFrame(date_range, columns=['YearMonth'])
        df['YearMonth'] = df['YearMonth'].dt.strftime('%Y-%m')
        df['Saving'] = df['YearMonth'].map(get_data_per_month)
        df['Asset Amount'] = df['Saving'].cumsum()
        df['Asset Amount (Rp)'] = df['Asset Amount'].map(format_rupiah)
        df['Balance Increase (Rp)'] = df['Saving'].map(format_rupiah)
        st.altair_chart(
            alt.Chart(df).mark_bar().encode(
                x='YearMonth', 
                y='Asset Amount',
                tooltip=['YearMonth', 'Asset Amount (Rp)', 'Balance Increase (Rp)']
            ).properties(height=400).interactive(), 
            use_container_width=True
        )
        
    def run(self):
        self.asset_action()
        df_out = self.get_asset_consumtion()
        df_in = self.get_incomes_history()
        self.load_current_asset()
        self.in_out_save(df_out, df_in)
        
        st.markdown(
                    f'<p class="header_text indian_color">Incomes History</p>', 
                    unsafe_allow_html=True
                )
        st.dataframe(df_in, height=300, use_container_width=True)
        self.get_history_asset_amount()
        
        # st.markdown(
        #     '<p class="header_text indian_color">Asset Consumption</p>', unsafe_allow_html=True)
        # st.altair_chart(alt.Chart(df_out).mark_bar().encode(
        #         x=alt.X('month_year:O', title='', axis=alt.Axis(labels=False)),
        #         y='sum(amount):Q',
        #         color='month_year:O',
        #         column= alt.Column('affected_asset:N',
        #             title="",
        #             header=alt.Header(
        #                 labelAngle=-90, 
        #                 labelOrient='bottom',
        #                 orient='bottom',
        #                 labelAlign='right'
        #             ),
        #         ),
        #     ))