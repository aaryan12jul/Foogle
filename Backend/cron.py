from crawler import fooglebot
import psycopg2
import time, random

for i in range(5):
    print(f"Waiting for PostgreSQL to start...{i}")
    try:
        connection = psycopg2.connect(
            database="foogle_db",
            user="foogle",
            password="foogle",
            host="foogle-db",
            port="5432"  # Default is 5432
        )
        print("Connection to PostgreSQL established successfully")
        break
    except psycopg2.Error as e:
        print("Error connecting to PostgreSQL:", e)
    finally:
        time.sleep(2)
else:
    print("PostgreSQL did not start after multiple attempts. Exiting.")
    exit(1)

cursor = connection.cursor()

# Creating Table
cursor.execute("""CREATE TABLE IF NOT EXISTS indexed_pages (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    words TEXT[] NOT NULL
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS args (
    id SERIAL PRIMARY KEY,
    visited_urls TEXT[] NOT NULL,
    CRAWL_LIMIT INTEGER NOT NULL
)""")

# Commit the changes to the database
connection.commit()

# Start the crawler
starting_urls = None
try:
    while True:
        # Fetch the last row from the args table
        cursor.execute("SELECT * FROM args ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        if last_row is None:
            args = None
        else:
            args = {
                    'visited_urls': last_row[1] if random.randint(1, 10) != 1 else set(), 
                    'CRAWL_LIMIT': last_row[2],
                    'indexed_pages': []
                }

        # Crawling
        indexed_pages, args = fooglebot(args, starting_urls)

        # Insert indexed pages into the database
        for page in indexed_pages:
            cursor.execute(
                """
                INSERT INTO indexed_pages (url, title, description, words)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (url) DO UPDATE
                SET title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    words = EXCLUDED.words
                """,
                (page["url"], page["title"], page["description"], page["words"])
            )

        cursor.execute("SELECT * FROM args ORDER BY id DESC LIMIT 1")
        if cursor.fetchone() is None:
            # If no args exist, insert the initial args
            cursor.execute(
                "INSERT INTO args (visited_urls, CRAWL_LIMIT) VALUES (%s, %s)",
                (list(args['visited_urls']), args['CRAWL_LIMIT'])
            )
        else:
            # Update the args table with the latest visited URLs and crawl limit
            cursor.execute(
                """UPDATE args SET (visited_urls, CRAWL_LIMIT) = (%s, %s) WHERE id = %s""", 
                (list(set(args['visited_urls'])), args['CRAWL_LIMIT'], 1)
            )

        # Commit the changes to the database
        connection.commit()

        cursor.execute("SELECT * FROM args ORDER BY id DESC LIMIT 1")
        print("Length of Visited URLS", len(cursor.fetchone()[1]))

        if args['crawl_count'][0] < 0.1 * args['CRAWL_LIMIT']:
            starting_urls = [random.choice(args['visited_urls']) for _ in range(5)]
        
        time.sleep(5)
except psycopg2.Error as e:
    print("Error during crawling:", e)
    # Close the cursor and connection
    cursor.close()
    connection.close()
    exit()