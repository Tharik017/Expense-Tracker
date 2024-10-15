import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import base64
from datetime import datetime
from database import create_table, register_user, verify_user




# Create the users table if it doesn't exist
create_table()
st.markdown(
    """
    <style>
    header {
        visibility: hidden;  /* Hides the header */
        height: 0;           /* Prevents spacing issues */
    }
    </style>
    """,
    unsafe_allow_html=True
)
# Initialize the app
st.title("Personal Expense Tracker")

# Initialize session state variables
if 'user_authenticated' not in st.session_state:
    st.session_state.user_authenticated = False
if 'show_register' not in st.session_state:
    st.session_state.show_register = False
if 'logout_confirmed' not in st.session_state:
    st.session_state.logout_confirmed = False

# Header section
st.title("Welcome to the App")

# Toggle Login/Register View
if st.session_state.show_register:
    # Show back to login button when in registration mode
    if st.button("Back to Login"):
        st.session_state.show_register = False
else:
    if st.button("Register"):
        st.session_state.show_register = True

# Only show the login/register forms if the user is not authenticated
if not st.session_state.user_authenticated:
    if st.session_state.show_register:
        # Registration Form
        st.subheader("Register")
        
        st.write("Or register with email:")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Create Password", key="reg_password", type='password')
        confirm_password = st.text_input("Confirm Password", key="confirm_password", type='password')

        if st.button("Register", key="register"):
            if reg_password == confirm_password:
                register_user(reg_email, reg_password)  # Implement this function in your database module
                st.success("Registration successful! Please login.")
                st.session_state.show_register = False
            else:
                st.error("Passwords do not match.")

    else:
        # Login Form
        st.subheader("Login")

        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", key="login_password", type='password')

        if st.button("Login", key="login"):
            if verify_user(login_email, login_password):  # Implement this function in your database module
                st.session_state.user_authenticated = True
                st.session_state.show_register = False  # Ensure registration form is hidden
                st.success("Logged in successfully!")

# If authenticated, show the main app functionality
if st.session_state.user_authenticated:
    st.write("🎉 Welcome to your dashboard!")
    
    # Load existing data or create a new DataFrame
    @st.cache_data
    def load_data():
        try:
            data = pd.read_csv('transactions.csv', parse_dates=['Date'])
            if 'Status' not in data.columns:
                data['Status'] = 'Pending'
            return data
        except FileNotFoundError:
            return pd.DataFrame(columns=['Date', 'Description', 'Category', 'Amount', 'Status'])

    # Function to generate a download link for CSV
    def download_link(df, filename):
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()  # bytes
        return f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV</a>'

    # Load transactions into session state
    if 'transactions' not in st.session_state:
        st.session_state.transactions = load_data()

    # Add Transaction Form
    st.header("Add a Transaction")
    with st.form(key='transaction_form'):
        date = st.date_input("Date", key="date_input", help="Select the date of the transaction")
        time = st.time_input("Time", value=datetime.now().time(), key="time_input")  # Current time input
        description = st.text_input("Description", key="description", help="Enter a brief description")
        category = st.selectbox("Category", ["Food", "Transport", "Utilities", "Entertainment", "Healthcare", "Groceries", "Other"], key="category")
        amount = st.number_input("Amount (in Rupees)", min_value=0.0, format="%.2f", key="amount", help="Enter the transaction amount")
        status = st.selectbox("Status", ["Pending", "Completed"], key="status")  # New status column
        
        submit_button = st.form_submit_button("Add Transaction", help="Click to add the transaction")

        if submit_button:
            if amount <= 0:
                st.error("Amount must be greater than zero.")
            else:
                # Combine date and time into a single datetime object
                transaction_datetime = pd.to_datetime(f"{date} {time}")
                # Add the transaction to the DataFrame
                new_transaction = pd.DataFrame({
                    'Date': [transaction_datetime],
                    'Description': [description],
                    'Category': [category],
                    'Amount': [amount],
                    'Status': [status],  # Add status to the new transaction
                })
                st.session_state.transactions = pd.concat([st.session_state.transactions, new_transaction], ignore_index=True)
                st.session_state.transactions.to_csv('transactions.csv', index=False)  # Save the transactions
                st.success("Transaction added!")

    # Search by date
    st.header("Search Transactions by Date")
    search_date = st.date_input("Select a date to filter transactions")

    # Ensure the 'Date' column is in datetime format
    st.session_state.transactions['Date'] = pd.to_datetime(st.session_state.transactions['Date'], errors='coerce')

    # Filter transactions for the selected date
    filtered_transactions = st.session_state.transactions[st.session_state.transactions['Date'].dt.date == search_date]

    # Display the transactions
    st.header("Transactions")
    if filtered_transactions.empty:
        st.write("No transactions recorded for this date.")
    else:
        # Group transactions by date
        grouped_transactions = filtered_transactions.groupby('Date')

        for date, group in grouped_transactions:
            st.subheader(f"Transactions on {date.date()}")
            group = group.reset_index(drop=True)  # Reset index for the group DataFrame
            group['S.No'] = range(1, len(group) + 1)  # Create Serial Number column
            st.dataframe(group[['S.No', 'Date', 'Description', 'Category', 'Amount', 'Status']])

        # Provide a download link for CSV
        st.markdown(download_link(filtered_transactions, 'filtered_transactions.csv'), unsafe_allow_html=True)

    # Display all transactions if no filter applied
    if st.session_state.transactions.empty:
        st.write("No transactions recorded yet.")
    else:
        # Sort transactions by date
        st.session_state.transactions = st.session_state.transactions.sort_values(by='Date', ascending=False).reset_index(drop=True)

        # Display transactions in a table with a delete option
        st.subheader("All Transactions")

        # Selectbox for deletion
        transaction_to_delete = st.selectbox("Select a transaction to delete", 
                                            options=[f"{index}: {row['Description']} - {row['Amount']} Rupees ({row['Status']})" 
                                                        for index, row in st.session_state.transactions.iterrows() if row['Status'] != 'Deleted'])
        
        if st.button("Delete Selected Transaction"):
            index_to_delete = int(transaction_to_delete.split(":")[0])  # Extract index from selected option
            st.session_state.transactions = st.session_state.transactions.drop(st.session_state.transactions.index[index_to_delete]).reset_index(drop=True)
            st.session_state.transactions.to_csv('transactions.csv', index=False)  # Save the updated transactions
            st.success("Transaction deleted!")

        # Show updated transaction table
        st.dataframe(st.session_state.transactions)

        # Provide a download link for CSV
        st.markdown(download_link(st.session_state.transactions, 'transactions.csv'), unsafe_allow_html=True)

    # Visualize spending
    if not st.session_state.transactions.empty:
        st.header("Spending Overview")
        
        # Group by category and sum amounts
        spending = st.session_state.transactions.groupby('Category')['Amount'].sum().reset_index()

        # Create a pie chart
        fig, ax = plt.subplots()
        ax.pie(spending['Amount'], labels=spending['Category'], autopct='%1.1f%%', startangle=90)
        ax.axis('equal')  # Equal aspect ratio ensures that pie chart is circular
        st.pyplot(fig)

    # Budgeting Feature
    st.header("Budgeting")
    budget = st.number_input("Set a monthly budget", min_value=0.0, format="%.2f")
    if budget > 0:
        total_spending = st.session_state.transactions['Amount'].sum()
        st.write(f"Total Spending: ₹{total_spending:.2f}")
        if total_spending > budget:
            st.warning("You have exceeded your budget!")
        else:
            st.success("You are within your budget!")

    # Tax Calculation Feature
    st.header("Tax Calculation")
    income = st.number_input("Enter your total income for the year", min_value=0.0)
    tax_rate = st.selectbox("Select your tax rate (%)", [5, 10, 15, 25, 30, 35, 40], index=1)  # 10%, 20%, 30%, 40%
    if income > 0:
        estimated_tax = income * (tax_rate / 100)
        st.write(f"Estimated Tax: ₹{estimated_tax:.2f}")

    # Logout functionality with confirmation
    if st.button("Logout"):
        st.session_state.logout_confirmed = True

    if st.session_state.logout_confirmed:
        st.write("Are you sure you want to logout?")
        if st.button("Yes, Logout"):
            st.session_state.user_authenticated = False
            st.session_state.show_register = False
            st.session_state.logout_confirmed = False  # Reset confirmation
            st.success("Logged out successfully!")
        if st.button("No, Stay Logged In"):
            st.session_state.logout_confirmed = False  # Reset confirmation
