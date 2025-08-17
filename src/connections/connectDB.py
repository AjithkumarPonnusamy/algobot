import psycopg2


# PostgreSQL connection
conn = psycopg2.connect(
    host="localhost",
    port="5432",
    database="algo",
    user="postgres",
    password="ak"
)


