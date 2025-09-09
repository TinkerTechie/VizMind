from flask import Flask, render_template, request, flash, redirect, url_for
import pandas as pd
import os
from gtts import gTTS
import uuid # Used for creating unique filenames

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Ensure the upload and static folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

def generate_pandas_insights(df):
    """
    Generates a dictionary of data insights from a pandas DataFrame.
    """
    insights = {}

    # 1. Basic Information (Shape)
    num_rows, num_cols = df.shape
    insights['Data Shape'] = f"Analysis complete! Your dataset has {num_rows} rows and {num_cols} columns."
    insights['Data Types'] = df.dtypes.to_frame('Data Type').to_html(classes='table-auto w-full text-left')
    missing_values = df.isnull().sum()
    missing_df = missing_values[missing_values > 0].to_frame('Missing Values')
    if not missing_df.empty:
        insights['Missing Values'] = missing_df.to_html(classes='table-auto w-full text-left')
    else:
        insights['Missing Values'] = "<p>No missing values found in the dataset. Great!</p>"
    numeric_description = df.describe().to_html(classes='table-auto w-full text-left')
    insights['Statistical Summary (Numeric Columns)'] = numeric_description
    if 'object' in df.dtypes.values or 'category' in df.dtypes.values:
         insights['Statistical Summary (Categorical Columns)'] = df.describe(include=['object', 'category']).to_html(classes='table-auto w-full text-left')
    insights['Data Preview (First 5 Rows)'] = df.head().to_html(classes='table-auto w-full text-left', index=False)
    return insights

def create_voice_summary(df):
    """
    Creates a natural language summary string from the DataFrame for TTS.
    """
    try:
        num_rows, num_cols = df.shape
        summary_parts = [f"Analysis complete! Your dataset has {num_rows} rows and {num_cols} columns."]

        # Missing values check
        if df.isnull().sum().sum() == 0:
            summary_parts.append("No missing values were found.")
        else:
            summary_parts.append("The dataset contains some missing values that may need attention.")

        # Numeric summary
        numeric_cols = df.select_dtypes(include=['number']).columns
        if not numeric_cols.empty:
            summary_parts.append("Here is a summary of the key numerical columns.")
            # Summarize up to 3 numeric columns to keep it brief
            for col in numeric_cols[:3]:
                col_mean = df[col].mean()
                col_max = df[col].max()
                summary_parts.append(f"For {col.replace('_', ' ')}, the average is {col_mean:.2f}, and the maximum value is {col_max:.2f}.")

        return ' '.join(summary_parts)
    except Exception as e:
        print(f"Error creating voice summary: {e}")
        return "Could not generate a voice summary due to an error."


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and file.filename.endswith('.csv'):
        try:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            df = pd.read_csv(filepath)
            insights = generate_pandas_insights(df)

            # --- New Voice Output Logic ---
            # 1. Create the text summary for the voice
            summary_text = create_voice_summary(df)

            # 2. Generate the audio file from the text
            tts = gTTS(text=summary_text, lang='en', slow=False)
            
            # 3. Save the audio file with a unique name
            audio_filename = f"summary_{uuid.uuid4().hex}.mp3"
            audio_filepath = os.path.join('static', audio_filename)
            tts.save(audio_filepath)
            # --- End of New Logic ---

            # Pass insights, filename, and the new audio file to the template
            return render_template('index.html', insights=insights, filename=file.filename, audio_file=audio_filename)

        except Exception as e:
            print(f"Error processing file: {e}")
            flash(f"An error occurred while processing the file: {e}")
            return redirect(url_for('home'))
    else:
        flash('Invalid file type. Please upload a CSV file.')
        return redirect(request.url)


if __name__ == '__main__':
    app.run(debug=True)
