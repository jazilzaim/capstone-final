import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f" * Argus API Product launching on http://{host}:{port}")
    print(" * Supported Municipalities: Las Vegas (NV), Los Angeles (CA), Seattle (WA), Phoenix (AZ)")
    print(" * Developer Playground: http://127.0.0.1:5000/playground")
    app.run(host=host, port=port, debug=True)
