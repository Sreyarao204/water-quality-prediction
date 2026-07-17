from flask import Flask, render_template, request, redirect, session
from model import train_model, predict_water, get_water_usage, get_feature_importance_from_input
from model import get_model_performance
from model import get_precautions
import os
import matplotlib
matplotlib.use('Agg')   # 🔥 IMPORTANT FIX
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from flask import send_file
import sqlite3
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = 'secret123'

# ✅ FIX: Define upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ Ensure folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# ---------------- DATABASE ---------------- #
# ---------------- DATABASE ---------------- #
import sqlite3

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # ✅ Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
    ''')

    # ✅ History Table (NEW)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            ph REAL,
            Hardness REAL,
            Solids REAL,
            Chloramines REAL,
            Sulfate REAL,
            Conductivity REAL,
            Organic_carbon REAL,
            Trihalomethanes REAL,
            Turbidity REAL,
            result TEXT
        )
    ''')

    conn.commit()
    conn.close()

# Initialize database
init_db()


# ---------------- AUTH ---------------- #

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        return render_template('signup.html', message="Account created! Please login.")

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()

        conn.close()

        if user:
            session['user'] = username
            return redirect('/')
        else:
            return render_template('login.html', message="Invalid credentials")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')


# ---------------- PROTECTED HOME ---------------- #
@app.route('/')
def home():
    if 'user' not in session:
        return redirect('/login')

    return render_template('index.html')


# ---------------- UPLOAD ---------------- #
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        file = request.files.get('file')

        if file and file.filename != "":
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            # Save dataset path in session
            session['dataset'] = filepath

            return render_template('data/upload.html', message="Dataset uploaded successfully!")

    return render_template('data/upload.html')


# ---------------- PREDICTION ---------------- #
@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    if 'user' not in session:
        return redirect('/login')

    usage = []   # ✅ FIX: initialize first

    if request.method == 'POST':
        if 'dataset' not in session:
            return render_template('data/prediction.html', result="Please upload dataset first")

        filepath = session['dataset']

        try:
            model = train_model(filepath)

            ph = float(request.form['ph'])
            Hardness = float(request.form['Hardness'])
            Solids = float(request.form['Solids'])
            Chloramines = float(request.form['Chloramines'])
            Sulfate = float(request.form['Sulfate'])
            Conductivity = float(request.form['Conductivity'])
            Organic_carbon = float(request.form['Organic_carbon'])
            Trihalomethanes = float(request.form['Trihalomethanes'])
            Turbidity = float(request.form['Turbidity'])

            inputs = [
                ph, Hardness, Solids, Chloramines,
                Sulfate, Conductivity, Organic_carbon,
                Trihalomethanes, Turbidity
            ]

            result = predict_water(model, inputs)

            feature_names = [
                "pH", "Hardness", "Solids", "Chloramines",
                "Sulfate", "Conductivity", "Organic Carbon",
                "Trihalomethanes", "Turbidity"
            ]

            importance = get_feature_importance_from_input(inputs, feature_names)
            session['importance'] = importance



            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO history (
                    username, ph, Hardness, Solids, Chloramines,
                    Sulfate, Conductivity, Organic_carbon,
                    Trihalomethanes, Turbidity, result
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session['user'], ph, Hardness, Solids, Chloramines,
                Sulfate, Conductivity, Organic_carbon,
                Trihalomethanes, Turbidity, result
            ))

            conn.commit()
            conn.close()

            # ✅ ALWAYS create usage
            usage = get_water_usage(result, inputs)

            # Store for charts
            session['result'] = result
            session['chart_data'] = {
                "ph": ph,
                "Hardness": Hardness,
                "Solids": Solids,
                "Chloramines": Chloramines,
                "Sulfate": Sulfate,
                "Conductivity": Conductivity,
                "Organic_carbon": Organic_carbon,
                "Trihalomethanes": Trihalomethanes,
                "Turbidity": Turbidity
            }


        except Exception as e:
            result = "Error: " + str(e)
            usage = ["Prediction failed. Please check input values."]  # ✅ fallback

        return render_template('data/prediction.html', result=result, usage=usage)

    return render_template('data/prediction.html')


@app.route('/charts')
def charts():
    if 'user' not in session:
        return redirect('/login')

    data = session.get('chart_data', {})

    return render_template(
        'analysis/charts.html',
        result=session.get('result', 'Safe'),
        ph=data.get('ph', 7),
        hardness=data.get('Hardness', 150),
        solids=data.get('Solids', 500),
        chloramines=data.get('Chloramines', 5),
        sulfate=data.get('Sulfate', 300),
        conductivity=data.get('Conductivity', 1000),
        organic=data.get('Organic_carbon', 5),
        trihalo=data.get('Trihalomethanes', 50),
        turbidity=data.get('Turbidity', 3)
    )

@app.route('/performance')
def performance():
    if 'user' not in session:
        return redirect('/login')

    if 'dataset' not in session:
        return "Upload dataset first"

    filepath = session['dataset']

    accuracy, precision, recall, f1, cm = get_model_performance(filepath)

    return render_template(
        'insights/performance.html',
        accuracy=round(accuracy*100,2),
        precision=round(precision*100,2),
        recall=round(recall*100,2),
        f1=round(f1*100,2),
        cm=cm
    )

@app.route('/precautions')
def precautions():
    if 'user' not in session:
        return redirect('/login')

    result = session.get('result', None)

    if result is None:
        return "No prediction data available"

    precautions_list = get_precautions(result)

    return render_template(
        'analysis/precautions.html',
        result=result,
        precautions=precautions_list
    )

@app.route('/data')
def data_module():
    return render_template('modules/data.html')

@app.route('/analysis')
def analysis_module():
    return render_template('modules/analysis.html')

@app.route('/insights')
def insights_module():
    return render_template('modules/insights.html')

@app.route('/reports')
def reports():
    return render_template('modules/reports.html')

@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM history WHERE username=?", (session['user'],))
    data = cursor.fetchall()

    conn.close()

    return render_template('insights/history.html', data=data)


import pandas as pd
from flask import send_file

@app.route('/download')
def download_report():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM history WHERE username=?", (session['user'],))
    data = cursor.fetchall()
    conn.close()

    file_path = "final_report.pdf"
    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()

    content = []

    # 🔥 TITLE
    content.append(Paragraph("Water Quality Analysis Report", styles['Title']))
    content.append(Spacer(1, 20))

    for row in data:

        # ---------------- INPUT TABLE ---------------- #
        content.append(Paragraph(f"<b>Prediction ID:</b> {row[0]}", styles['Heading3']))
        content.append(Spacer(1, 10))

        table_data = [
            ["Parameter", "Value"],
            ["pH", row[2]],
            ["Hardness", row[3]],
            ["Solids", row[4]],
            ["Chloramines", row[5]],
            ["Sulfate", row[6]],
            ["Conductivity", row[7]],
            ["Organic Carbon", row[8]],
            ["Trihalomethanes", row[9]],
            ["Turbidity", row[10]],
        ]

        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]))

        content.append(table)
        content.append(Spacer(1, 10))

        # ---------------- RESULT ---------------- #
        result_color = "green" if row[11] == "Safe" else "red"

        content.append(Paragraph(
            f"<b>Prediction Result:</b> <font color='{result_color}'>{row[11]}</font>",
            styles['Normal']
        ))

        content.append(Spacer(1, 10))

        # ---------------- PRECAUTIONS ---------------- #
        if row[11] == "Safe":
            precautions = [
                "Safe for drinking",
                "Store properly",
                "Avoid contamination"
            ]
        else:
            precautions = [
                "Boil water before use",
                "Use filtration",
                "Avoid direct drinking"
            ]

        content.append(Paragraph("<b>Precautions:</b>", styles['Heading4']))

        for p in precautions:
            content.append(Paragraph(f"• {p}", styles['Normal']))

        content.append(Spacer(1, 15))

        # ---------------- CHART GENERATION ---------------- #
        labels = [
            "pH", "Hardness", "Solids", "Chloramines",
            "Sulfate", "Conductivity", "Organic Carbon",
            "Trihalomethanes", "Turbidity"
        ]

        values = [
            row[2], row[3], row[4], row[5],
            row[6], row[7], row[8],
            row[9], row[10]
        ]

        plt.figure(figsize=(6,4))
        plt.bar(labels, values)
        plt.xticks(rotation=45)
        plt.title("Water Parameters Chart")

        chart_path = f"chart_{row[0]}.png"
        plt.tight_layout()
        plt.savefig(chart_path)
        plt.close()

        # Add chart to PDF
        content.append(Paragraph("<b>Visual Representation:</b>", styles['Heading4']))
        content.append(Image(chart_path, width=400, height=250))

        content.append(Spacer(1, 25))

    doc.build(content)

    # Cleanup chart images
    for row in data:
        chart_file = f"chart_{row[0]}.png"
        if os.path.exists(chart_file):
            os.remove(chart_file)

    return send_file(file_path, as_attachment=True)


@app.route('/feature-importance')
def feature_importance():
    importance = session.get('importance', [])
    print("SESSION DATA:", importance)   # 🔥 ADD THIS

    return render_template('reports/importance.html', data=importance)

# ---------------- RUN ---------------- #
if __name__ == '__main__':
    app.run(debug=True)++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++