import joblib
import os
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

# Training Data - Isse AI seekhta hai
DATA = [
    ("Starbucks coffee", "Food"), ("Zomato food", "Food"), ("Pizza dinner", "Food"),
    ("Uber ride", "Travel"), ("Ola taxi", "Travel"), ("Petrol for bike", "Travel"),
    ("Netflix monthly", "Entertainment"), ("Movie tickets", "Entertainment"),
    ("Airtel bill", "Bills"), ("Electricity bill", "Bills"), ("Rent", "Bills"),
    ("Amazon shopping", "Shopping"), ("Flipkart clothes", "Shopping"), ("Groceries", "Food")
]

def get_model_path():
    return os.path.join(os.path.dirname(__file__), 'expense_model.pkl')

def train_model():
    texts, labels = zip(*DATA)
    model = Pipeline([
        ('vectorizer', CountVectorizer()),
        ('classifier', MultinomialNB())
    ])
    model.fit(texts, labels)
    joblib.dump(model, get_model_path())

def suggest_category(description):
    if not description: return "Others"
    
    path = os.path.join(os.path.dirname(__file__), 'expense_model.pkl')
    
    # Agar model file nahi hai, toh train karo
    if not os.path.exists(path):
        texts, labels = zip(*DATA)
        model = Pipeline([('v', CountVectorizer()), ('nb', MultinomialNB())])
        model.fit(texts, labels)
        joblib.dump(model, path)
    
    model = joblib.load(path)
    try:
        return model.predict([description])[0]
    except:
        return "Others"