import sys
import os
import streamlit as st
from datetime import datetime
from streamlit import session_state as ss
import pandas as pd
from streamlit_extras.stylable_container import stylable_container
import altair as alt
import streamlit.components.v1 as components

import warnings
warnings.filterwarnings('ignore')

this_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(this_dir)
from utils import *

class Expenses:
    def __init__(self, **kwargs):
        self.df_cat = pd_read_sql('select * from categories')
        self.df_budget = pd_read_sql('select * from budgets', ['category', 'amount'])
        self.assets = kwargs.get('assets')
        self.months = kwargs.get('months')

    def push_new_category(self):
        new_category_name = clean_text(ss['new_category_name'])
        if new_category_name == '':
            components.html("<script>alert('Category name is required!')</script>", height=0, width=0)
        elif new_category_name in self.df_cat['category_name'].tolist():
            components.html("<script>alert('Category name is already exists!')</script>", height=0, width=0)
        else:
            data_dict = {
                'category_name' : new_category_name,
                'description' : clean_text(ss['new_category_desc'])
            }
            insert_data("categories", data_dict)

    @st.experimental_dialog("Enter Category Details")
    def input_new_category(self):
        st.text_input("Category Name", max_chars=25, key='new_category_name')
        st.text_input("Description", max_chars=100, key='new_category_desc')
        if st.button("Submit"):
            self.push_new_category()
            update_data_repo('categories')
            st.rerun()

    def categories_content(self):
        with st.expander("Categories"):
            st.data_editor(
                self.df_cat, 
                height=300, 
                use_container_width=True,
                on_change=on_change_data,
                args = (self.df_cat, 'categories'),
                key = 'category_edited',
                disabled = ('id', 'category_name', )
            )

            with stylable_container(
                "add_categories_button",
                css_styles="""
                button {
                    background-color: #FF4B4B;
                    color: white;
                }
                """,
            ):
                if st.button("Add Categories"):
                    self.input_new_category()

    def push_new_expenses(self):
        unit_price = int(ss["new_expenses_unit_price"])
        quantity = int(ss["new_expenses_input_quantity"])
        total_amount = unit_price * quantity
        data_dict = {
            "date"          : add_timenow(ss["new_expenses_transaction_date"]),
            "item_name"     : clean_text(ss["new_expenses_item_name"]),
            "category"      : ss["new_expenses_selected_category"],
            "unit_price"    : unit_price,
            "quantity"      : quantity,
            "total_amount"  : total_amount,
            "affected_asset": ss["new_expenses_selected_assets"],
        }
        insert_data('expenses', data_dict)

    @st.experimental_dialog("Enter Expense Details")
    def input_new_expenses(self):
        st.text_input("item name", max_chars=25, key="new_expenses_item_name")
        st.selectbox("select category", self.df_cat['category_name'], key='new_expenses_selected_category')
        st.number_input("unit price", min_value=1, value=1000, step=100, key='new_expenses_unit_price')
        st.number_input("input quantity", min_value=1, step=1, key='new_expenses_input_quantity')
        st.selectbox("select asset resource", self.assets, key='new_expenses_selected_assets')
        st.date_input("transaction date", key='new_expenses_transaction_date', max_value=datetime.now()+timedelta(hours=7))
        if st.button("Submit"):
            self.push_new_expenses()
            update_data_repo('expenses')
            st.rerun()

    def get_month_data(self, selected_month):
        year, month = selected_month.split('-')
        sql = '''
            SELECT * FROM expenses 
            WHERE strftime('%Y', date) = '{}' AND strftime('%m', date) = '{}' AND category NOT LIKE '%asset%'
            ORDER BY date
            '''.format(year, month)
        df = pd_read_sql(sql)
        df['date'] = pd.to_datetime(df['date'], format='mixed')
        return df
    
    def agg_day_cat(self, df):
        df_out_per_day_cat = df.set_index('date').groupby([pd.Grouper(freq='D'), 'category'])['total_amount'].sum().reset_index()
        df_out_per_day = df_out_per_day_cat.groupby('date')[['total_amount']].sum().reset_index()
        df_out_per_day = df_out_per_day.resample('D', on='date').sum().reset_index()
        df_out_per_day = self.fill_missing_date(df_out_per_day)
        return df_out_per_day_cat, df_out_per_day
    
    def get_a_month_summary(self, df, df_day_agg):
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
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<p class='center_align'>Total Expenses</p>", unsafe_allow_html=True)
            st.markdown(
                '<p class="center_align header_text indian_color">{}</p>'.format(
                        format_rupiah(df['total_amount'].sum())
                    ), unsafe_allow_html=True)
        with col2:
            st.markdown("<p class='center_align'>Average Daily Expenses</p>", unsafe_allow_html=True)
            st.markdown(
                '<p class="center_align header_text indian_color">{}</p>'.format(format_rupiah(df_day_agg['total_amount'].mean())), unsafe_allow_html=True)
            
    def daily_charts(self, df, df_day_cat, df_day):
        def chart_stacked_bar_and_line():
            stacked_chart = alt.Chart(df_day_cat).mark_bar().encode(
                        x='date(date):O',
                        y='sum(total_amount)',
                        color='category'
                    ).interactive()
            line_chart = alt.Chart(df_day).mark_line(interpolate='monotone').encode(
                            x='date(date):O',
                            y='total_amount'                
                        ).interactive()
            st.markdown("<p class='center_align' style='font-weight: bold; font-size:20px;'>Expenses per Day per Category</p>", unsafe_allow_html=True)
            st.altair_chart(alt.layer(stacked_chart, line_chart), use_container_width=True)

        def chart_bar():
            df_per_cat = df.groupby('category')[['total_amount']].sum().reset_index()
            df_per_cat['percent_amount'] = df_per_cat['total_amount']/df_per_cat['total_amount'].sum()
            st.markdown("<p class='center_align'>{}</p>".format('Top 5 Category'), unsafe_allow_html=True)
            st.altair_chart(
                alt.Chart(df_per_cat).mark_bar().encode(
                    y=alt.X('category', sort='-x'), 
                    x='total_amount',
                    color=alt.Color('category', legend=None),
                    tooltip=[
                        'category',  'total_amount',
                        alt.Tooltip('percent_amount', format='.2%')
                    ]
                ).properties(height=400).interactive(), 
                use_container_width=True
            )

        def chart_pie_top_5():
            top_categories = df_day_cat.groupby('category')[['total_amount']].sum().reset_index()
            top_categories = top_categories[top_categories['total_amount']>0]
            top_categories['percent_amount'] = top_categories['total_amount']/top_categories['total_amount'].sum()
            top_categories = top_categories.sort_values('percent_amount').reset_index(drop=True)
            top_categories['cumsum_percent'] = top_categories['percent_amount'].cumsum()
            nearest_idx = (top_categories['cumsum_percent'] - 0.07).abs().idxmin()
            top_categories.loc[:nearest_idx, "category"] = "others"
            top_categories = top_categories.groupby("category")[["total_amount"]].sum()
            top_categories = top_categories.sort_values('total_amount', ascending=False).reset_index()
            top_categories["labels"] = top_categories['total_amount'].map(
                lambda x: ' {} ({:.1f}%)'.format(
                    format_label(x),
                    x/top_categories['total_amount'].sum()*100
                    )
                )
            base = alt.Chart(top_categories).encode(
                alt.Theta("total_amount").stack(True),
                alt.Color("category"),
            ).interactive()

            pie = base.mark_arc(outerRadius=100, innerRadius=50)
            text = base.mark_text(radius=140, size=10).encode(text="labels:N")
            
            st.markdown("<p class='center_align' style='font-weight: bold; font-size:20px;'>Top 5 Expenses Category</p>", unsafe_allow_html=True)
            st.altair_chart(pie + text, use_container_width=True)


        chart_stacked_bar_and_line()
        chart_pie_top_5()
        chart_bar()

    def fill_missing_date(self, df):
        year, month = df['date'].iloc[0].year, df['date'].iloc[0].month
        if year == 2024 and month == 4:
            start = df['date'].min()
        else:
            start = datetime(year, month, 1)
        if year == datetime.now().year and month == datetime.now().month:
            end = datetime.now() + timedelta(hours=7)
        else:
            end = datetime(year, month, df['date'].max().day)
        df.set_index('date', inplace=True)
        full_date_range = pd.date_range(start=start, end=end)
        df = df.reindex(full_date_range)
        df['total_amount'] = df['total_amount'].fillna(0)
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'date'}, inplace=True)
        return df

    def get_details_summary(self, group_by, add_condition=None):
        condition = "category not like '%asset%'"
        if add_condition is not None:
            condition += ' {}'.format(add_condition)

        sql = f"""
            SELECT 
				category,
                strftime('%Y-%m', date) AS YearMonth,
                SUM(total_amount) AS TotalExpenses,
                SUM(total_amount) / (
                    CASE 
                        WHEN strftime('%Y-%m', date) = '2024-04' THEN 16
                        WHEN strftime('%Y-%m', date) = strftime('%Y-%m', date('now')) THEN CAST(strftime('%d', datetime('now', '+7 hours')) AS INTEGER)
                        ELSE CAST(strftime('%d', date(date, 'start of month', '+1 month', '-1 day')) AS INTEGER) 
                    END
                ) AS AvgDailyExpenses
            FROM 
                expenses
            WHERE
                {condition}
            GROUP BY 
                {', '.join(group_by)};
        """
        return pd_read_sql(sql)

    def daily_content(self):
        if 'selected_month' not in ss:
            selected_month = self.months[0]
        else:
            selected_month = ss['selected_month']
        
        df = self.get_month_data(selected_month)
        col1, col2 = st.columns([0.2, 0.8])
        with col1:
            selected_month = st.selectbox('Select Month', self.months, key='selected_month')
        # with col3:
        #     if st.checkbox("All"):
        #         options = df['category'].unique().tolist()
        #     else:
        #         options = None
        with col2:
            filtered_category = st.multiselect(
                'Filter Category', 
                df['category'].unique().tolist(), 
                default = None
            )
            if filtered_category:
                df = df[df['category'].isin(filtered_category)]
        
        df = df.sort_values('id', ascending=False).reset_index(drop=True)
        df_day_cat_agg, df_day_agg = self.agg_day_cat(df)
        self.get_a_month_summary(df, df_day_agg)

        df_details_per_cat = self.get_details_summary(['YearMonth', 'category'], f"AND YearMonth='{selected_month}'")
        df_details_per_cat = df_details_per_cat.sort_values('TotalExpenses', ascending=False).reset_index(drop=True)
        df_details_per_cat['Percent'] = df_details_per_cat['TotalExpenses']/df_details_per_cat['TotalExpenses'].sum()
        df_details_per_cat['AvgDailyExpenses'] = df_details_per_cat['AvgDailyExpenses'].map(format_rupiah)
        # df_details_per_cat['TotalExpenses'] = df_details_per_cat['TotalExpenses'].map(format_rupiah)
        df_details_per_cat['Percent'] = df_details_per_cat['Percent'].map(lambda x: '{:.2f} %'.format(x*100))

        st.markdown("<p class='center_align' style='font-weight: bold; font-size:25px;'> ⚠️⚠️⚠️Budgeting Alert!!!⚠️⚠️⚠️</p>", unsafe_allow_html=True)
        for i, row in self.df_budget.iterrows():
            category = row['category']
            budget = row['amount']
            try:
                expenses = df_details_per_cat[df_details_per_cat['category']==category]['TotalExpenses'].iloc[0]
            except:
                expenses = 0
            progress_bar(category, budget, expenses)
        st.write("")
        
        with st.expander("Daily Expenses Table"):
            delete_data = st.button('Delete Row')
            placeholder = st.empty()
            placeholder.dataframe(
                df, 
                height=300, use_container_width=True)
            if delete_data:
                placeholder.empty()
                st.data_editor(
                    df, 
                    height=300, 
                    use_container_width=True,
                    on_change=on_change_data,
                    args = (df, 'expenses'),
                    key = 'expenses_edited',
                    num_rows = 'dynamic',
                    disabled = tuple(df.columns)
                )
        
        with st.expander("Details per Category Table"):
            st.dataframe(
                df_details_per_cat,
                height=300,
                use_container_width=True
            )

        with st.expander('Charts'):
            self.daily_charts(df, df_day_cat_agg, df_day_agg)

    def get_monthly_expenses(self):
        query = """SELECT 
                    strftime('%Y-%m', date) as month_year,
                    category, 
                    sum(total_amount) as amount
                FROM expenses
                WHERE 
                    category NOT LIKE '%asset%'
                GROUP BY
                    category, strftime('%Y-%m', date)
                """
        return pd_read_sql(query)

    def monthly_content(self):
        def monthly_history():
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("<p>Period</p>", unsafe_allow_html=True)
                for row in df_monthly_summ['YearMonth']:
                    # st.markdown(f"<p class='vertical_center'>{row}</p>", unsafe_allow_html=True)
                    st.markdown(
                        f'<p class="header_text">{row}</p>', 
                        unsafe_allow_html=True
                    )
                    # st.write(row)
            with col2:
                st.markdown("<p class='center_align'>Total Expenses</p>", unsafe_allow_html=True)
                for row in df_monthly_summ['TotalExpenses']:
                    st.markdown(
                        f'<p class="center_align header_text indian_color">{format_label(row)}</p>', 
                        unsafe_allow_html=True
                    )
            with col3:
                st.markdown("<p class='center_align'>Average Daily Expenses</p>", unsafe_allow_html=True)
                for row in df_monthly_summ['AvgDailyExpenses']:
                    st.markdown(
                        f'<p class="center_align header_text indian_color">{format_label(row)}</p>', 
                        unsafe_allow_html=True
                    )
            
        def chart_bar():
            st.markdown("<p class='center_align' style='font-weight: bold; font-size:20px;'>Total Expenses</p>", unsafe_allow_html=True)
            st.altair_chart(
                alt.Chart(df.groupby('month_year')[['amount']].sum().reset_index(),).mark_bar().encode(
                    x='month_year', 
                    y='amount'
                ).properties(height=400).interactive(), 
                use_container_width=True
            )

        def chart_grouped_bar(df, y_column):
            st.altair_chart(alt.Chart(df).mark_bar().encode(
                x=alt.X('YearMonth:O', title='', axis=alt.Axis(labels=False)),
                y=f'{y_column}:Q',
                color='YearMonth:O',
                # column=alt.Column'category:O'
                column= alt.Column('category:N',
                    title="",
                    header=alt.Header(
                        labelAngle=-90, 
                        labelOrient='bottom',
                        orient='bottom',
                        labelAlign='right'
                    ),
                ),
                tooltip=[
                        'YearMonth', f'{y_column} (Rp)'
                    ]
            ).interactive())

        def chart_100_stacked_bar():
            st.markdown("<p class='center_align' style='font-weight: bold; font-size:20px;'>Top 5 Category</p>", unsafe_allow_html=True)
            top5 = []
            for month_year in df['month_year'].unique():
                sub_df = df[df['month_year']==month_year]
                sub_df['amount_percent'] = sub_df['amount']/sub_df['amount'].sum()
                top5.append(sub_df[sub_df['amount_percent']>0.05])
                tmp = sub_df[sub_df['amount_percent']<=0.05]
                top5.append(pd.DataFrame({
                        'month_year': [month_year], 'category': ['other'], 
                        'amount': tmp['amount'].sum(),
                        'amount_percent': tmp['amount_percent'].sum()
                    }))
            top5 = pd.concat(top5)
            
            top5['label'] = top5['amount'].map(format_label)
            st.altair_chart(
                alt.Chart(top5)
                    .transform_joinaggregate(total_amount='sum(amount)')
                    # .transform_calculate(amount_percent='datum.amount/datum.total_amount')
                    .mark_bar().encode(
                    x='month_year',
                    y=alt.X('amount').stack('normalize'),
                    color=alt.Color('category'),
                    tooltip=[
                        'category',
                        alt.Tooltip('label', title='Expenses'),
                        alt.Tooltip('amount_percent:Q', title='Expenses(%)', format='.2%')
                    ]
                ).properties(height=400).interactive(), 
                use_container_width=True
            )
            return top5

        df = self.get_monthly_expenses()
        df_monthly_summ = self.get_details_summary(['YearMonth'])
        with st.expander("Monthly History", expanded=True):
            monthly_history()

        # chart_bar()
        top5 = chart_100_stacked_bar()
        df_monthly_summ_per_cat = self.get_details_summary(['YearMonth', 'category'])
        df_monthly_summ_per_cat = df_monthly_summ_per_cat[df_monthly_summ_per_cat['category'].isin(top5['category'])]
        df_monthly_summ_per_cat['TotalExpenses (Rp)'] = df_monthly_summ_per_cat['TotalExpenses'].map(format_rupiah)
        df_monthly_summ_per_cat['AvgDailyExpenses (Rp)'] = df_monthly_summ_per_cat['AvgDailyExpenses'].map(format_rupiah)
        
        st.markdown("<p class='center_align' style='font-weight: bold; font-size:20px;'>Average Daily Expenses Category</p>", unsafe_allow_html=True)
        chart_grouped_bar(df_monthly_summ_per_cat, 'AvgDailyExpenses')

        st.markdown("<p class='center_align' style='font-weight: bold; font-size:20px;'>Total Monthly Expenses Category</p>", unsafe_allow_html=True)
        chart_grouped_bar(df_monthly_summ_per_cat, 'TotalExpenses')        

    @st.experimental_dialog("Edit Budget")
    def edit_budget(self):
        category = st.selectbox("select category", self.df_budget['category'], key='budget_category')
        amount = st.number_input("budget per month", min_value=1, value=1000, step=100, key='budget_amount')
        if st.button("Submit"):
            data_dict = {
                "category"  : category,
                "amount"    : int(amount)
            }
            update_data('budgets', data_dict, f"category = '{category}'")
            st.rerun()
    
    @st.experimental_dialog("Add Budget")
    def input_new_budget(self):
        st.selectbox("select category", self.df_cat['category_name'], key='new_budget_category')
        st.number_input("budget per month", min_value=1, value=1000, step=100, key='new_budget_amount')
        if st.button("Submit"):
            if len(self.df_budget)>0:
                if ss["new_budget_category"] in self.df_budget['category'].tolist():
                    components.html("<script>alert('Category name is already exists!')</script>", height=0, width=0)
                    return None
            data_dict = {
                "category"  : ss["new_budget_category"],
                "amount"    : int(ss["new_budget_amount"])
            }
            insert_data('budgets', data_dict)
            update_data_repo('budgets')
            st.rerun()

    def budgeting(self):   
        if len(self.df_budget)>0:
            if 'selected_month' not in ss:
                selected_month = self.months[0]
            else:
                selected_month = ss['selected_month']
            self.df_budget['amount per day'] = self.df_budget['amount']/get_num_days(selected_month)
            self.df_budget['amount per day'] = self.df_budget['amount per day'].map(lambda x: round(x, 2))
        with st.expander('Budgeting'):
            col1, col2 = st.columns(2)
            with col1:
                with stylable_container(
                    "add_expenses_button",
                    css_styles=css_button_style
                ):
                    if st.button("Add Budget"):
                        self.input_new_budget()
            with col2:
                with stylable_container(
                    "add_expenses_button",
                    css_styles=css_button_style
                ):
                    if st.button("Edit Budget"):
                        self.edit_budget()
            st.dataframe(
                self.df_budget, 
                height=300, 
                use_container_width=True
            )  

    def run(self):
        col1, col2, col3 = st.columns([0.2,0.4,0.4])
        with col1:
            with stylable_container(
                "add_expenses_button",
                css_styles=css_button_style
            ):
                if st.button("Add Expenses"):
                    self.input_new_expenses()
        with col2:
            self.budgeting()

        with col3:
            self.categories_content()
        
        tab_daily, tab_monthly = st.tabs(['Daily', 'Monthly'])
        with tab_daily:
            self.daily_content()

        with tab_monthly:
            self.monthly_content()
