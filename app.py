import traceback
import os
from flaskr import create_app

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Create app with configuration
app = create_app()

if __name__ == '__main__':
    app.run(debug=False)
