from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from openai import OpenAI
import stripe
import os

app = Flask(__name__)
CORS(app)

# Rate limiting: 3 requests/day per IP
limiter = Limiter(get_remote_address, app=app, default_limits=["3 per day"])

# GPT-4 Turbo
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Stripe setup
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID")

@app.route('/')
def index():
    return render_template("form.html")

@app.route('/success')
def success():
    return "<h2>Subscription successful!</h2><p>You now have unlimited access to IB Essay Grader.</p>"

def prompt_router(subject, paper, essay):
    subject = subject.strip().lower()
    paper = paper.strip().lower()

    if subject == "english a" and paper == "paper 1":
        return f"""
You are an IB English A: Language and Literature examiner. Grade the following Paper 1 textual analysis using the official IB rubric:

- Criterion A: Understanding and Interpretation (0–5)
- Criterion B: Analysis and Evaluation (0–5)
- Criterion C: Focus and Organization (0–5)
- Criterion D: Language (0–5)

Provide:
1. A score for each criterion
2. A short explanation for each
3. 2 suggestions for improvement

Essay:
\"\"\"
{essay}
\"\"\"
        """

    elif subject == "theory of knowledge" and paper == "essay":
        return f"""
You are an IB Theory of Knowledge examiner. Grade the following TOK essay using the official IB rubric:

- A: Scope (0–10)
- B: Understanding (0–10)
- C: Analysis and argument (0–10)
- D: Organization (0–10)
- E: Language (0–10)

Provide:
1. Score for each criterion
2. Justification
3. 2 improvement suggestions

Essay:
\"\"\"
{essay}
\"\"\"
        """

    elif subject == "economics" and paper == "paper 1":
        return f"""
You are an IB Economics examiner. Grade the following Paper 1 essay. Use the IB criteria:

- A: Knowledge and understanding of theory (0–10)
- B: Application and analysis (0–10)
- C: Synthesis and evaluation (0–10)
- D: Diagrams (0–4)
- E: Terminology (0–2)

Provide:
- Score per criterion
- Justification
- 2 improvement points

Essay:
\"\"\"
{essay}
\"\"\"
        """

    elif subject == "history" and paper in ["paper 2", "paper 3"]:
        return f"""
You are an IB History examiner. Grade the following Paper {paper[-1]} essay using the standard rubric:

- Focus and method (0–8)
- Knowledge and understanding (0–8)
- Critical thinking (0–8)

Give:
- Score for each criterion
- Brief reasoning
- 2 improvement suggestions

Essay:
\"\"\"
{essay}
\"\"\"
        """

    elif subject == "theory of knowledge" and paper == "exhibition":
        return f"""
You are a TOK examiner grading a TOK Exhibition commentary. Use the rubric for TOK Exhibition assessment.

Grade based on:
- Justification of object selection
- Connection to IA prompt
- Engagement with TOK concepts

Give:
- Overall score (out of 10)
- Justification
- 2 feedback points

Essay:
\"\"\"
{essay}
\"\"\"
        """

    # Default fallback
    return f"""
You are an IB examiner. Grade the following essay using appropriate IB criteria. Provide:

- Score per relevant criterion
- Short explanations
- Overall feedback
- 2 suggestions for improvement

Essay:
\"\"\"
{essay}
\"\"\"
    """

@app.route('/grade', methods=['POST'])
@limiter.limit("3 per day")
def grade_essay():
    try:
        if request.is_json:
            data = request.get_json()
            essay = data.get("essay", "")
            subject = data.get("subject", "")
            paper = data.get("paper", "")
        else:
            essay = request.form.get("essay", "")
            subject = request.form.get("subject", "")
            paper = request.form.get("paper", "")

        if not essay or not subject or not paper:
            return jsonify({"error": "Essay, subject, or paper missing."}), 400

        prompt = prompt_router(subject, paper, essay)

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        feedback = response.choices[0].message.content
        return jsonify({"feedback": feedback})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        if not STRIPE_PRICE_ID:
            return jsonify({"error": "Stripe Price ID not set."}), 400

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            success_url='https://your-replit-url.repl.co/success',
            cancel_url='https://your-replit-url.repl.co/',
        )
        return jsonify({'url': session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

app.run(host='0.0.0.0', port=81)