from flask import Flask, render_template, request, flash, url_for, redirect, send_from_directory
import pandas as pd
from gtts import gTTS
import os
import uuid

# --- START OF THE FIX ---
# Get the absolute path of the directory the script is in (e.g., /var/task/api)
basedir = os.path.abspath(os.path.dirname(__file__))

# Initialize Flask by explicitly telling it where the template and static folders are.
# The paths are relative to this script's location.
app = Flask(__name__,
            template_folder=os.path.join(basedir, '../templates'),
            static_folder=os.path.join(basedir, '../static'))
# --- END OF THE FIX ---


# Vercel uses a temporary directory, so we need a reliable path for writes.
UPLOAD_FOLDER = '/tmp/uploads'
STATIC_FOLDER = '/tmp/static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'supersecretkey' # Needed for flash messages

# This function generates the insights from the dataframe
def generate_pandas_insights(df):
    insights = {}
    insights['Data Shape'] = f"The dataset has {df.shape[0]} rows and {df.shape[1]} columns."
    
    # Data Types
    dtype_df = df.dtypes.to_frame('Data Type').astype(str)
    insights['Data Types'] = dtype_df.to_html(classes="table-auto w-full text-left")

    # Missing Values
    missing_values = df.isnull().sum()
    if missing_values.sum() == 0:
        insights['Missing Values'] = "<p>No missing values found in the dataset. Great!</p>"
    else:
        missing_df = missing_values.to_frame('Missing Count')
        insights['Missing Values'] = missing_df.to_html(classes="table-auto w-full text-left")

    # Statistical Summary (Numeric)
    numeric_summary = df.describe(include='number')
    if not numeric_summary.empty:
        insights['Statistical Summary (Numeric Columns)'] = numeric_summary.to_html(classes="table-auto w-full text-left")

    # Statistical Summary (Categorical)
    categorical_summary = df.describe(include=['object', 'category'])
    if not categorical_summary.empty:
        insights['Statistical Summary (Categorical Columns)'] = categorical_summary.to_html(classes="table-auto w-full text-left")
    
    insights['Data Preview (First 5 Rows)'] = df.head().to_html(classes="table-auto w-full text-left")
    return insights

# This function creates the voice summary
def create_voice_summary(df):
    rows, cols = df.shape
    summary_text = f"Analysis complete. The dataset has {rows} rows and {cols} columns. "
    numeric_cols = df.select_dtypes(include='number').columns
    if len(numeric_cols) > 0:
        col = numeric_cols[0]
        summary_text += f"The average value for the first numeric column, {col}, is {df[col].mean():.2f}."
    return summary_text

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files or request.files['file'].filename == '':
        flash('No file selected. Please choose a CSV file.')
        return redirect(url_for('home'))

    file = request.files['file']
    filename = file.filename
    
    if not filename.lower().endswith('.csv'):
        flash('Invalid file type. Please upload a CSV file.')
        return redirect(url_for('home'))

    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        df = pd.read_csv(filepath)

        # Generate insights
        insights = generate_pandas_insights(df)
        
        # Generate voice summary
        summary_text = create_voice_summary(df)
        tts = gTTS(text=summary_text, lang='en')
        
        # Save audio to a unique file in the temporary static folder
        audio_filename = f"summary_{uuid.uuid4()}.mp3"
        audio_filepath = os.path.join(STATIC_FOLDER, audio_filename)
        tts.save(audio_filepath)
        
        # We now pass a special path for the audio file to the template
        audio_url = url_for('serve_generated_static', filename=audio_filename)
        return render_template('index.html', insights=insights, filename=filename, audio_url=audio_url)
    except Exception as e:
        flash(f'An error occurred: {str(e)}')
        return redirect(url_for('home'))

# Route to serve the generated static files (like audio) from the temporary directory
@app.route('/generated_static/<path:filename>')
def serve_generated_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)
