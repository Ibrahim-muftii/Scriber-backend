from app import create_app

app = create_app()

if __name__ == '__main__':
    print("Flask server is running....!")
    app.run(debug=True)
