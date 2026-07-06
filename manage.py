"""Development entrypoint: `python manage.py` runs the Flask dev server
(honours a supervisor-assigned PORT). Production uses wsgi.py + Gunicorn.
"""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Respect PORT when a supervisor assigns one; default stays 5000.
    app.run(port=int(os.environ.get("PORT", 5000)))
