import nltk
import ssl
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# nltk.download('stopwords')
# nltk.download('punkt_tab')

# Download NLTK data only if not already downloaded
def download_nltk_resources():
    try:
        stopwords.words('english')
    except LookupError:
        nltk.download('stopwords')
    try:
        word_tokenize('test')
    except LookupError:
        nltk.download('punkt_tab')

# Function that indexes the webpage
def index_page(webpage, webpage_url):
    download_nltk_resources()

    stop_words = set(stopwords.words('english'))
    ps = PorterStemmer()

    # Collect title
    title_tag = webpage.find('title')
    title = title_tag.get_text().strip() if title_tag else 'No Title'
    
    # Collect description from meta tag, or fallback to text
    description = ''
    meta_description = webpage.find('meta', attrs={'name': 'description'})
    if meta_description and 'content' in meta_description.attrs:
        description = meta_description['content']
    else:
        text_content = webpage.get_text(separator=" ", strip=True)
        description = text_content[:200] + "..." if len(text_content) > 200 else text_content
    
    # Grab all the words in the page
    text_content = webpage.get_text(separator=' ', strip=True)
    tokens = word_tokenize(text_content.lower())

    # Stemming the words and removing stop words
    filtered_words = [
        ps.stem(word) for word in tokens if word.isalpha() and word not in stop_words
    ]
    
    # Add the information to the index
    indexed_page = {
        "url": webpage_url,
        "title": title,
        "description": description,
        "words": filtered_words
    }

    return indexed_page

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

if __name__ == '__main__':
    # Test the indexing by loading a webpage and indexing it
    from bs4 import BeautifulSoup
    import requests

    url = "https://www.wikipedia.org/"
    response = requests.get(url)
    webpage = BeautifulSoup(response.content, "html.parser")
    
    # Index the page
    indexed_page = index_page(webpage, url)
    print(indexed_page)  # Print the result of indexing the page