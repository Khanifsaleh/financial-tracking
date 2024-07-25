import os
import sys
import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from datetime import datetime

this_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(this_dir)
from utils import *

class Receivables:
    def __init__(self, **kwargs):
        self.assets = kwargs.get('assets')

    @st.experimental_dialog("Add Receivable")
    def add_receivable(self):
        desc = st.text_input("Description", max_chars=25)
        asset = st.selectbox("Select Asset Source", self.assets+["In Past"])
        amount = st.number_input('Amount', min_value=500)
        date = st.date_input("Date", max_value=datetime.now())
        if st.button("Submit"):
            data_dict = {
                "date" : add_timenow(date),
                "description": desc,
                "affected_asset": asset,
                "amount": amount
            }
            insert_data('receivables', data_dict)
            update_data_repo('receivables')
            st.rerun()


    def action(self):
        # col1, col2, _ = st.columns([0.7,1.2,5])
        # with col1:
        with stylable_container(
            "asset_action_button",
            css_styles=css_button_style,
        ):
            if st.button("Add"):
                self.add_receivable()    
            
        # with col2:
        #     with stylable_container(
        #         "asset_action_button",
        #         css_styles=css_button_style,
        #     ):
        #         if st.button("Repayment"):
        #             self.transfer_asset()

    def get_data(self):
        df = pd_read_sql('select * from receivables')
        df = df.sort_values('date').reset_index(drop=True)
        del df['id']
        st.markdown(
            f'''
                <p class="header_text" style="float:left;">Total Piutang :&nbsp;&nbsp;</p><p class="header_text indian_color">{format_rupiah(df['amount'].sum())}</p>
            ''', 
            unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)

    def run(self):
        self.action()
        self.get_data()