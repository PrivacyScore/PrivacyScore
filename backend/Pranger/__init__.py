from flask import Flask
app = Flask(__name__)
app.route("/")
if __name__ == "__main__":
    app.run(debug=True, host="192.168.56.101", port=5000)
