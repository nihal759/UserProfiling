import pandas as pd
from sqlalchemy import create_engine
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import mean_squared_error, mean_absolute_error
import numpy as np
import joblib

# Database configuration
DATABASE_URL = "mssql+pyodbc://DESKTOP-K8BIO91\\SQLEXPRESS/profiling?driver=ODBC+Driver+17+for+SQL+Server"

# Create a database connection
engine = create_engine(DATABASE_URL)

# Query to get user interactions
query = """
SELECT user_id, video_id, watched
FROM user_interactions
"""
data = pd.read_sql(query, engine)

# Debugging print
print("Data loaded:")
print(data.head())
print(data.shape)

# Aggregate duplicates by taking the maximum of 'watched'
data = data.groupby(['user_id', 'video_id']).agg({'watched': 'max'}).reset_index()

# Debugging print
print("Aggregated Data:")
print(data.head())
print(data.shape)

# Create user-item interaction matrix
interaction_matrix = data.pivot(index='user_id', columns='video_id', values='watched').fillna(0)

# Debugging print
print("Interaction matrix:")
print(interaction_matrix.head())
print(interaction_matrix.shape)

# Create and train the model
svd = TruncatedSVD(n_components=5)

try:
    # Fit the SVD model
    interaction_matrix_svd = svd.fit_transform(interaction_matrix)
    interaction_matrix_reconstructed = svd.inverse_transform(interaction_matrix_svd)
    interaction_matrix_predicted = np.dot(interaction_matrix_svd, svd.components_)
    
    # Calculate reconstruction errors
    mse = mean_squared_error(interaction_matrix, interaction_matrix_reconstructed)
    mae = mean_absolute_error(interaction_matrix, interaction_matrix_reconstructed)
    
    # Print errors
    print(f"Mean Squared Error of Reconstruction: {mse}")
    print(f"Mean Absolute Error of Reconstruction: {mae}")

except Exception as e:
    print("Error during SVD computation:")
    print(e)
    raise

# Save the model and interaction matrix
joblib.dump(svd, 'svd_model.pkl')
joblib.dump(interaction_matrix, 'interaction_matrix.pkl')
