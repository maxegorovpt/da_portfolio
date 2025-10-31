import streamlit as st
import pandas as pd
import folium

# Load your CSV file
@st.cache
def load_data():
    df_geo = pd.read_csv('df_geo.csv', sep=';')
    return df_geo

# Streamlit UI
st.title('User Locations on Map')

# Load the data
data = load_data()

# Sidebar for user selection
user_id = st.sidebar.selectbox('Select a User ID:', data['user_id'].unique())

# Filter data based on user selection
user_data = data[data['user_id'] == user_id]

# Create a Folium map centered on the user's location
m = folium.Map(location=[user_data.iloc[0]['latitude'], user_data.iloc[0]['longitude']], zoom_start=12)

# Add markers for user locations with tooltips
for index, row in user_data.iterrows():
    folium.Marker([row['latitude'], row['longitude']], tooltip=f"User {row['user_id']}").add_to(m)

# Display the map
st.write(f"User {user_id}'s Locations:")
st.write(m)
