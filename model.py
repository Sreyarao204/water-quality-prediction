import pandas as pd
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score, f1_score
from imblearn.over_sampling import SMOTE

# ---------------- TRAIN MODEL ---------------- #
def train_model(filepath):

    # Detect file type
    if filepath.endswith('.csv'):
        data = pd.read_csv(filepath)
    else:
        data = pd.read_excel(filepath)

    # Remove missing values
    data = data.dropna()

    # Features & Target
    X = data.drop('Potability', axis=1)
    y = data['Potability']

    # Train model
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X, y)

    return model


# ---------------- PREDICTION ---------------- #
def predict_water(model, inputs):
    prediction = model.predict([inputs])
    return "Safe" if prediction[0] == 1 else "Unsafe"


# ---------------- WATER USAGE LOGIC ---------------- #
def get_water_usage(result, inputs):

    ph, Hardness, Solids, Chloramines, Sulfate, Conductivity, Organic_carbon, Trihalomethanes, Turbidity = inputs

    usage = []

    # Drinking Water
    if result == "Safe" and 6.5 <= ph <= 8.5 and Turbidity < 5:
        usage.append("Suitable for Drinking")

    # Agriculture
    if 6 <= ph <= 8.5 and Solids < 1000:
        usage.append("Suitable for Agriculture")

    # Industrial
    if Conductivity < 1500:
        usage.append("Suitable for Industrial Use")

    # Domestic
    if Turbidity < 10:
        usage.append("Suitable for Domestic Use")

    # Irrigation
    if Sulfate < 400:
        usage.append("Suitable for Irrigation")

    # Additional Conditions
    if Hardness < 200:
        usage.append("Good for Household Cleaning")

    if Organic_carbon < 10:
        usage.append("Low Organic Pollution - Environment Friendly")

    # If no conditions matched
    if not usage:
        usage.append("Not suitable for major uses. Water treatment required.")

    return usage



def get_model_performance(filepath):

    if filepath.endswith('.csv'):
        data = pd.read_csv(filepath)
    else:
        data = pd.read_excel(filepath)

    data = data.fillna(data.mean())

    X = data.drop('Potability', axis=1)
    y = data['Potability']

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        use_label_encoder=False,
        eval_metric='logloss',
        random_state=42
    )

    model.fit(X, y)

    y_pred = model.predict(X)

    accuracy = accuracy_score(y, y_pred)
    precision = precision_score(y, y_pred, zero_division=0)
    recall = recall_score(y, y_pred, zero_division=0)
    f1 = f1_score(y, y_pred, zero_division=0)

    cm = confusion_matrix(y, y_pred)

    return accuracy, precision, recall, f1, cm.tolist()

def get_precautions(result):

    precautions = []

    if result == "Safe":
        precautions.append("Water is safe for drinking")
        precautions.append("Store water in clean containers")
        precautions.append("Avoid contamination during storage")

    else:
        precautions.append("Boil water before drinking")
        precautions.append("Use water filters (RO/UV)")
        precautions.append("Avoid direct consumption")
        precautions.append("Use for industrial or irrigation purposes only")

    return precautions

def get_feature_importance_from_input(inputs, feature_names):

    total = sum(inputs)

    result = []

    for name, value in zip(feature_names, inputs):

        percent = round((value / total) * 100, 2)

        # Impact classification
        if percent > 25:
            impact = "High Impact"
        elif percent > 15:
            impact = "Medium Impact"
        else:
            impact = "Low Impact"

        result.append((name, percent, impact))

    # Sort highest first
    result.sort(key=lambda x: x[1], reverse=True)

    return result