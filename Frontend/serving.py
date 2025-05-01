from flask import Flask, request, jsonify
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
import nltk
import math, time
import threading, psycopg2

app = Flask(__name__)
indexed_pages = []
data_labels = ["url", "title", "description", "words"]

nltk.download('stopwords')
nltk.download('punkt_tab')

def connect_db():
    global indexed_pages
    
    # Connect to PostgreSQL database
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

    while True:
        # Fetch all indexed pages from the database
        cursor.execute("SELECT * FROM indexed_pages")
        table = cursor.fetchall()
        
        # Formatting the results
        indexed_pages = [{data_labels[i-1]: row[i] for i in range(1, len(row))} for row in table]
        time.sleep(5)  # Sleep for a while before fetching again

thread = threading.Thread(target=connect_db)
thread.daemon = True  # Daemonize thread
thread.start()  # Start the thread

def parse_query(query):
    stop_words = set(stopwords.words('english'))
    ps = PorterStemmer()
    # Tokenize the query
    tokens = word_tokenize(query.lower())
    # Remove non-alphabetic tokens and stop words, then stem the words
    query_words = [
        ps.stem(word.lower()) for word in tokens if word.isalpha() and word not in stop_words
    ]
    return query_words

# Function to compute PageRank using TF-IDF with Title Boost
def compute_pagerank(queries, results):
    for query in queries:
        for website in results:
            website["pagerank"] = 0

            # Boost pages where the title contains the query
            if website.get("title") and query.lower() in website["title"].lower():
                website["pagerank"] += 5  # Boost pages with matching title

            # Regular PageRank scoring based on word matches
            if website.get("words") is None:
                continue
            for word in website['words']:
                if word.lower() == query.lower():
                    website["pagerank"] += 1

    sorted_results = sorted(results, key=lambda x: x['pagerank'], reverse=True)
    return [result for result in sorted_results if result['pagerank'] > 0]  # Filter out zero scores

# Function to compute TF-IDF
def compute_tfidf(query, indexed_pages):
    term_freq = {}
    doc_freq = {}

    # Count the term frequency (TF) and document frequency (DF)
    for page in indexed_pages:
        for word in page["words"]:
            if word not in doc_freq:
                doc_freq[word] = 0
            if word not in term_freq:
                term_freq[word] = {}
            term_freq[word][page["url"]] = term_freq[word].get(page["url"], 0) + 1
            doc_freq[word] += 1

    # Calculate TF-IDF for each document
    tfidf_scores = []
    for page in indexed_pages:
        score = 0
        for word in query:
            tf = term_freq.get(word, {}).get(page["url"], 0)
            df = doc_freq.get(word, 0)
            if df > 0:
                idf = math.log(len(indexed_pages) / df)
                score += tf * idf
        tfidf_scores.append((page, score))

    # Sort the pages by their TF-IDF score
    sorted_results = sorted(tfidf_scores, key=lambda x: x[1], reverse=True)
    return [x[0] for x in sorted_results]

# Function to perform the search and return ranked results
def search(query, indexed_pages, num_results=10, page=1):
    query_words = parse_query(query)
    if not query_words:
        return []

    # First, compute TF-IDF ranking
    tfidf_results = compute_tfidf(query_words, indexed_pages)

    # Then, compute PageRank based on TF-IDF results
    pagerank_results = compute_pagerank(query_words, tfidf_results)

    # Pagination
    start = (page - 1) * num_results
    end = start + num_results
    paginated_results = pagerank_results[start:end]

    # Create a new list of results without "words"
    final_results = []
    for result in paginated_results:
        result_copy = result.copy()  # Create a shallow copy of the result
        if "words" in result_copy:
            del result_copy["words"]  # Remove the words from the copy
        final_results.append(result_copy)  # Append the modified copy to the result list

    return final_results

@app.route('/search')
def search_api():
    query = request.args.get('q', '')
    num_results = int(request.args.get('num_results', 10))
    page = int(request.args.get('page', 1))

    if not query:
        return jsonify({'error': 'No query provided'}), 400

    # Call the search function with the query
    if not indexed_pages:
        return jsonify({'error': 'No indexed pages available'}), 500
    results = search(query, indexed_pages, num_results=num_results, page=page)
    return jsonify({
        'query': query,
        'page': page,
        'num_results': num_results,
        'results': results
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)