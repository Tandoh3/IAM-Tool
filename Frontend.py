import streamlit as st
import pandas as pd
import io
from thefuzz import process, fuzz

# 🎨 Configure Streamlit Page
st.set_page_config(page_title="🔐 IAM Tool", layout="wide", initial_sidebar_state="expanded")

# 🌟 Sidebar Navigation
st.sidebar.image("https://via.placeholder.com/15", use_container_width=True)
st.sidebar.title("🔍**Navigation**")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "📌 Select Section:",
    ["🏠 Main Page","🔁 Duplicate User Provisioning", "📂 Database Groups", "🔑 Database Privilege Users", "🗂 Database Profiles"]
)
st.sidebar.markdown("---")
st.sidebar.info("**Use this tool to manage access securely!**")

@st.cache_data
def load_excel(file):
    return pd.read_excel(file)

def find_matching_rows(df, column_name, disengaged_staff_list, threshold=70):
    """Find matching rows in the uploaded file using fuzzy matching."""
    if column_name not in df.columns:
        st.error(f"Column '{column_name}' not found.")
        return pd.DataFrame()
    
    matched_rows = pd.concat([
        df[df[column_name].isin(
            [match for match, score in process.extract(name, df[column_name].tolist(), scorer=fuzz.token_sort_ratio) if score >= threshold]
        )]
        for name in disengaged_staff_list
    ]).drop_duplicates()
    
    return matched_rows

# Ensure session state variables are initialized
if "matched_results" not in st.session_state:
    st.session_state["matched_results"] = {}

if page == "🏠 Main Page":
    st.title("🏠 Identity Access Management Tool")
    
    # Step 1: Upload Disengaged Staff List
    st.header("Step 1: Upload Disengaged Staff List")
    disengaged_file = st.file_uploader("📂 Upload an Excel file", type=["xlsx"], key="disengaged")
    disengaged_list = []
    
    if disengaged_file:
        disengaged_df = load_excel(disengaged_file)
        disengaged_column = st.selectbox("🛑 Select column with disengaged staff names", disengaged_df.columns)
        disengaged_list = disengaged_df[disengaged_column].dropna().tolist()
        st.success("✅ Disengaged staff list uploaded.")
    
    # Step 2: Upload System Users List
    st.header("Step 2: Upload System Users List")
    app_file = st.file_uploader("📂 Upload an Excel file", type=["xlsx"], key="app")
    
    if app_file:
        app_df = load_excel(app_file)
        app_column = st.selectbox("🔎 Select column to match", app_df.columns, key="app_col")
        app_name = st.text_input("🖥️ Enter the system name", key="app_name")
        
        if st.button("🔍 Run Matching"):
            if app_name and disengaged_list:
                matched_df = find_matching_rows(app_df, app_column, disengaged_list)
                if not matched_df.empty:
                    st.session_state["matched_results"][app_name] = matched_df
                    st.success(f"✅ Matching completed for {app_name}.")
                else:
                    st.warning(f"No matches found for {app_name}.")
            else:
                st.warning("Please provide a system name and ensure the disengaged staff list is uploaded.")
            
            # Clear only the Step 2 fields by deleting their keys
            for key in ["app", "app_col", "app_name"]:
                if key in st.session_state:
                    del st.session_state[key]
            # No full rerun so that previous results remain intact.
    
    # Step 3: Download Consolidated Results
    # Show this step if there are any matched results.
    if st.session_state["matched_results"]:
        st.header("Step 3: Review and Download Results")
        
        # Show summary of matched results
        summary_df = pd.DataFrame([
            {"System": app, "Matches": len(data)} 
            for app, data in st.session_state["matched_results"].items()
        ])
        st.dataframe(summary_df)

        selected_app = st.selectbox("🔍 Select system to preview", list(st.session_state["matched_results"].keys()))
        if selected_app:
            st.dataframe(st.session_state["matched_results"][selected_app])

        # Consolidate results into one Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            for app, data in st.session_state["matched_results"].items():
                data.to_excel(writer, sheet_name=app, index=False)
        output.seek(0)

        st.download_button(
            label="📥 Download Consolidated Results",
            data=output,
            file_name="Consolidated_Results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

elif page == "🔁 Duplicate User Provisioning":
    st.title("🔁 Duplicate User Provisioning")
    uploaded_file = st.file_uploader("Upload System Users", type=["xls", "xlsx"])
    
    if not uploaded_file:
        st.info("Please upload an Excel file to proceed.")
        st.stop()
        
    sys_users = pd.read_excel(uploaded_file)
    username_column = st.selectbox("Select the column containing usernames", sys_users.columns)
    
    if not username_column:
        st.stop()

    # 1) Identify users with >1 provisioning
    vc = sys_users[username_column].value_counts()
    dup_users = vc[vc > 1].index.tolist()
    dup_df = sys_users[sys_users[username_column].isin(dup_users)]
    
    # 2) Show raw rows
    st.subheader("🔍 Raw Rows for Users with Multiple Provisions")
    st.dataframe(dup_df)
    
    # 3) Show summary
    summary = (
        dup_df[username_column]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "Username", username_column: "Occurrences"})
    )
    st.subheader("📊 Occurrence Summary")
    st.dataframe(summary)
    
    # 4) Download the raw duplicate rows
    if not dup_df.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            dup_df.to_excel(writer, sheet_name="Multiple_Provisions", index=False)
        buffer.seek(0)
        
        st.download_button(
            label="📥 Download Users with Multiple Provisions",
            data=buffer,
            file_name="users_multiple_provisions.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No users with multiple provisions to download.")


        
# Database Groups Page
elif page == "📂 Database Groups":
    st.title("📂 Database Groups Management")
    uploaded_file = st.file_uploader("📂 Upload BASIS DBA_USER REPORT", type=["xls", "xlsx"])
    if uploaded_file:
        db_users = pd.read_excel(uploaded_file)

        # Extract Unique Profiles 
        unique_profiles = db_users["PROFILE"].unique()

        # Select the profile to View its Users 
        selected_profile = st.selectbox("🔎 Select a Profile Name: ", unique_profiles)

        # Display Users for the Selected Resource
        profiles = db_users.groupby("PROFILE")
        users_df = profiles.get_group(selected_profile)
        st.subheader(f"🗂 Profiles for: **{selected_profile}**")
        st.dataframe(users_df)

        # Consolidate all profile users into one Excel file with separate sheets 
        import io 
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            for users in unique_profiles:
                group = db_users[db_users["PROFILE"] == users]
                # Limit sheet name to 31 characters (Excel limitations)
                sheet_name = users[:31]
                group.to_excel(writer, sheet_name=sheet_name, index=False)
        output.seek(0)

        st.download_button(
            label = "📥 Download Consolidated Users of Profiles", 
            data = output, 
            file_name=" Consolidated_Users_of_Profiles.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )



# Database Privilege Users Page
elif page == "🔑 Database Privilege Users":
    st.title("🔑 Database Privilege Users")
    uploaded_file = st.file_uploader("📂 Upload BASIS DBA_ROLE_PRIVS", type=["xlsx"], key="db_priv")
    if uploaded_file:
        db_priv_df = pd.read_excel(uploaded_file)

        # Extract Unique Admin Options 
        unique_admin_names = db_priv_df['ADMIN OPTION'].unique()
        
        # Select an Admin Option to View its Users
        selected_admin = st.selectbox("🔎 Select Admin Option", db_priv_df["ADMIN OPTION"].unique())

        # Display Users for the Selected Resource 
        admin = db_priv_df.groupby('ADMIN OPTION')
        users_df = admin.get_group(selected_admin)
        st.subheader(f"Users for Admin Option: **{selected_admin}**")
        st.dataframe(users_df)

        # 📤 Consolidate all resource groups into one Excel file with separate sheets
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            for users in unique_admin_names:
                group = db_priv_df[db_priv_df["ADMIN OPTION"] == users]
                # Limit sheet name to 31 characters (Excel limitation)
                sheet_name = users[:31]
                group.to_excel(writer, sheet_name=sheet_name, index=False)
        output.seek(0)

        st.download_button(
            label="📥 Download Users in Admin Options",
            data=output,
            file_name="Consolidated_Admin_Options_Users.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Database Profiles Page
elif page == "🗂 Database Profiles":
    st.title("🗂 Database Profiles")
    uploaded_file = st.file_uploader("📂 Upload BASIS_DBA_PROFILES", type=["xls", "xlsx"])

    if uploaded_file:
        database_profile = pd.read_excel(uploaded_file)

        # 🎯 Extract Unique Resource Names
        unique_resource_names = database_profile['RESOURCE NAME'].unique()

        # 🔍 Select a Resource Name to View its Users
        selected_resource = st.selectbox("🔎 Select a Resource Name:", unique_resource_names)

        # 🎲 Display Users for the Selected Resource
        profiles = database_profile.groupby('RESOURCE NAME')
        users_df = profiles.get_group(selected_resource)
        st.subheader(f"🗂 Profiles for: **{selected_resource}**")
        st.dataframe(users_df)

        # 📤 Consolidate all resource groups into one Excel file with separate sheets
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            for resource in unique_resource_names:
                group = database_profile[database_profile["RESOURCE NAME"] == resource]
                # Limit sheet name to 31 characters (Excel limitation)
                sheet_name = resource[:31]
                group.to_excel(writer, sheet_name=sheet_name, index=False)
        output.seek(0)

        st.download_button(
            label="📥 Download Consolidated Profiles",
            data=output,
            file_name="Consolidated_Profiles.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
