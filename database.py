import pyodbc
def create_connection():
    connection = pyodbc.connect(r'DRIVER={SQL Server};SERVER=DESKTOP-K8BIO91\SQLEXPRESS;DATABASE=profiling')

    return connection