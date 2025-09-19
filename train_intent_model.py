import pickle
import re

# Third-party imports
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import train_test_split


def normalize_text(s: str) -> str:
    """
    Normalize text by stripping, converting to lowercase,
    and replacing multiple spaces with a single space.

    Args:
        s (str): Input text string.

    Returns:
        str: Normalized text string.
    """
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


# ===== 1) Đọc & tiền xử lý dữ liệu =====
data = pd.read_csv("dataset.csv")
data["text"] = data["text"].astype(str).map(normalize_text)
data["intent"] = data["intent"].astype(str)


# ===== 2) Tách train/test =====
X_train, X_test, y_train, y_test = train_test_split(
    data["text"],
    data["intent"],
    test_size=0.2,
    random_state=42,
    stratify=data["intent"]
)


# ===== 3) TF-IDF (char n-grams giúp robust cho TV có dấu/không dấu) =====
vectorizer = TfidfVectorizer(
    analyzer="char",
    ngram_range=(3, 5),
    min_df=1
)
Xtr = vectorizer.fit_transform(X_train)
Xte = vectorizer.transform(X_test)


# ===== 4) Logistic Regression =====
# multinomial + sag/saga thường tốt với nhiều lớp;
# ở đây ít lớp -> 'lbfgs' là đủ
clf = LogisticRegression(
    max_iter=200,
    multi_class="auto",
    solver="lbfgs"
)
clf.fit(Xtr, y_train)


# ===== 5) Đánh giá nhanh =====
pred = clf.predict(Xte)
print("Accuracy:", accuracy_score(y_test, pred))
print(classification_report(y_test, pred, digits=4))


# ===== 6) Lưu model =====
with open("intent_model.pkl", "wb") as f:
    pickle.dump((vectorizer, clf), f)

print(">> Đã lưu model vào intent_model.pkl")
