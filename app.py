from flask import Flask, render_template, request, jsonify
import pandas as pd
import openai
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Replace with your OpenAI API key or use local model
openai.api_key = "YOUR_OPENAI_API_KEY"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        file = request.files['file']
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        # Load CSV with pandas
        df = pd.read_csv(filepath)

        # Generate basic data description
        description = df.describe().to_string()

        # Ask OpenAI for insights based on description
        prompt = f"Here is a data description:\n{description}\n\nProvide a few insights in simple language."
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a data insights generator."},
                {"role": "user", "content": prompt}
            ]
        )

        insights = response['choices'][0]['message']['content']

        return render_template('index.html', insights=insights)

    except Exception as e:
        print("Error:", str(e))
        return jsonify({'message': 'Something went wrong.'})

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True)
